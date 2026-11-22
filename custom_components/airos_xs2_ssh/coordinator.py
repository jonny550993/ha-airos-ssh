import asyncio
import asyncssh
import logging
import re
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _to_text(val) -> str:
    if val is None:
        return ""
    if isinstance(val, (bytes, bytearray)):
        return val.decode(errors="ignore")
    return str(val)


def _number(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class AiRXS2Coordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host, username, password, name):
        self.host = host
        self.username = username
        self.password = password
        self.device_name = name
        self._previous_cpu_stats = None

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{name}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _run_command(self, conn, command):
        """Run a read-only command; ignore stderr to avoid leaking error text into sensors."""
        async with conn.create_process(command) as proc:
            stdout = await proc.stdout.read()
            await proc.stderr.read()
            await proc.wait()
        return _to_text(stdout)

    async def _async_update_data(self):
        try:
            async with asyncssh.connect(
                self.host,
                username=self.username,
                password=self.password,
                known_hosts=None,
                kex_algs=["diffie-hellman-group1-sha1"],
                encryption_algs=["aes128-cbc"],
                server_host_key_algs=["ssh-rsa"],
            ) as conn:
                output = await self._run_command(conn, "mca-status")
                if "=" not in output:
                    raise UpdateFailed(
                        f"mca-status returned no key=value output: {output[:200]}"
                    )
                data = self._parse_output(output)

                # Legacy airOS builds differ significantly. Probe commands
                # independently; missing commands/files are ignored so one
                # unsupported probe cannot break core sensors.
                probes = (
                    ("uptime", "cat /proc/uptime"),
                    ("loadavg", "cat /proc/loadavg"),
                    ("meminfo", "cat /proc/meminfo"),
                    ("cpu_stat", "cat /proc/stat"),
                    ("cpu_top", "top -b -n2 -d1"),
                    ("cpuinfo", "cat /proc/cpuinfo"),
                    ("version", "cat /etc/version"),
                    ("board", "cat /etc/board.info"),
                    ("system_cfg", "cat /tmp/system.cfg"),
                    ("uname", "uname -a"),
                    ("free", "free"),
                    ("date", "date"),
                    ("ps", "ps"),
                    ("logread", "logread | tail -n 20"),
                    ("df", "df -h"),
                    ("mount", "mount"),
                    ("ifconfig", "ifconfig"),
                    ("netdev", "cat /proc/net/dev"),
                    ("route", "route -n"),
                    ("arp", "arp -n"),
                    ("brctl", "brctl show"),
                    ("iwconfig", "iwconfig ath0"),
                    ("athstats", "athstats"),
                    ("wstalist", "wstalist"),
                    ("iwlist_scan", "iwlist ath0 scan"),
                )
                for name, command in probes:
                    try:
                        result = await self._run_command(conn, command)
                        self._parse_probe(name, result, data)

                        # Very old airOS kernels (including XS5 v4.x) expose only
                        # four /proc/stat counters. The first sample establishes a
                        # baseline, so take a second sample immediately rather than
                        # leaving CPU Usage unknown until the next HA polling cycle.
                        if name == "cpu_stat" and "cpu_usage" not in data:
                            await asyncio.sleep(1)
                            second_sample = await self._run_command(conn, "cat /proc/stat")
                            self._parse_probe("cpu_stat", second_sample, data)
                    except Exception as err:
                        _LOGGER.debug("airOS probe %s unavailable: %s", name, err)

                self._post_process(data)
                self._update_firmware_upgrade_status(data)
                return data

        except UpdateFailed:
            raise
        except Exception as e:
            raise UpdateFailed(f"SSH error: {e}") from e

    def _parse_output(self, output: str):
        data = {}
        for line in output.splitlines():
            if "=" in line:
                key, value = line.strip().split("=", 1)
                data[key] = value.strip()

        # Some legacy AirOS versions bundle identity metadata into side_devicename,
        # e.g. "UBNT,deviceId=...,firmwareVersion=...,platform=...,deviceIp=...".
        # Split those fields into their own values so Home Assistant can expose
        # them as individual sensors instead of hiding them in the name sensor.
        for key, value in list(data.items()):
            # Depending on the AirOS generation, identity metadata is returned
            # under side_devicename or deviceName. Both may contain a comma-
            # separated metadata blob rather than just a human-readable name.
            if key.lower() not in {"side_devicename", "devicename"}:
                continue
            parts = [part.strip() for part in value.split(",")]
            data[key] = parts[0] or "AirOS Device"
            metadata_keys = {
                "deviceid": "deviceId",
                "firmwareversion": "firmwareVersion",
                "platform": "platform",
                "deviceip": "deviceIp",
            }
            for part in parts[1:]:
                if "=" not in part:
                    continue
                metadata_key, metadata_value = part.split("=", 1)
                canonical_key = metadata_keys.get(metadata_key.strip().lower())
                metadata_value = metadata_value.strip()
                if canonical_key and metadata_value:
                    data.setdefault(canonical_key, metadata_value)

            # Keep the legacy side_devicename entity ID working if the device
            # reports its name using the newer deviceName key.
            if key.lower() == "devicename":
                data.setdefault("side_devicename", data[key])
                data.pop(key, None)

        # Some firmware returns the metadata blob in hostname/hostName or other keys.
        for key, value in list(data.items()):
            if not isinstance(value, str):
                continue
            lower_val = value.lower()
            if ",deviceid=" in lower_val or ",firmwareversion=" in lower_val or ",platform=" in lower_val:
                parts = [p.strip() for p in value.split(",")]
                clean_name = parts[0] or "AirOS Device"
                metadata_keys = {
                    "deviceid": "deviceId",
                    "firmwareversion": "firmwareVersion",
                    "platform": "platform",
                    "deviceip": "deviceIp",
                }
                for part in parts[1:]:
                    if "=" not in part:
                        continue
                    mk, mv = part.split("=", 1)
                    ck = metadata_keys.get(mk.strip().lower())
                    if ck and mv.strip():
                        data.setdefault(ck, mv.strip())
                data[key] = clean_name
                if key.lower() in {"hostname", "host.name", "host"}:
                    data.setdefault("device_name", clean_name)
                    data.setdefault("hostname", clean_name)

        # Canonicalise firmware-specific spellings into stable main-device sensors.
        lookup = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in data.items()}
        aliases = {
            "firmwareVersion": ("firmwareVersion", "firmware_version", "fwversion", "firmware", "version"),
            "apmac": ("apmac","ap_mac","apmacaddr","wlan_apmac"),
            "cfg_crc": ("cfgcrc","cfg_crc","configcrc","config_crc"),
            "distance": ("distance","linkdistance","dist"),
            "ack_timeout": ("acktimeout","ack_timeout"),
            "latitude": ("latitude","lat"), "longitude": ("longitude","lon","lng"),
            "radio_date_time": ("datetime","radio_datetime","date_time","radio_date_time"),
            "ppp_ip": ("pppip","ppp_ip","pppaddress"),
            "lan_ip_address": ("lan_ip_address", "lip", "lan_ip", "ethernet_ip_address"),
            "lan_mac_address": ("lan_mac_address", "lmac", "ethernet_mac_address"),
        }
        for target, candidates in aliases.items():
            for candidate in candidates:
                value = lookup.get(re.sub(r"[^a-z0-9]", "", candidate))
                if value not in (None, ""):
                    data.setdefault(target, value)
                    break

        # Keep installed firmware under one canonical key. Prefer explicit
        # firmware fields, but accept legacy status.cgi/mca-status spellings.
        if data.get("firmwareVersion") not in (None, ""):
            for alias in ("firmware_version", "fwversion", "firmware", "version"):
                alias_key = next(
                    (key for key in data if re.sub(r"[^a-z0-9]", "", str(key).lower())
                     == re.sub(r"[^a-z0-9]", "", alias)),
                    None,
                )
                if alias_key is not None and alias_key != "firmwareVersion":
                    data.pop(alias_key, None)
        self._identify_device(data, output)

        # Expose only one canonical uptime sensor, populated by the procfs probe.
        # airOS firmware may also report uptime-like keys in mca-status; discard
        # those aliases so they cannot create duplicate entities.
        for key in list(data):
            if key.lower() in {"uptime", "uptime_seconds", "systemuptime"}:
                data.pop(key, None)

        # Missing or malformed readings must stay unavailable, not look like real zeroes.
        for key in ("signal", "noise", "wlanTxRate", "wlanRxRate", "frequency"):
            value = _number(data.get(key))
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value

        raw_ccq = _number(data.get("ccq"))
        if raw_ccq is None:
            data.pop("ccq", None)
        else:
            # AirOS mca-status reports CCQ in tenths of a percent.
            data["ccq"] = raw_ccq / 10

        if "signal" in data and "noise" in data:
            data["snr"] = data["signal"] - data["noise"]
        else:
            data.pop("snr", None)
        return data

    @staticmethod
    def _identify_device(data, extra_output=""):
        """Identify original airOS 3.x-4.x hardware from legacy metadata."""
        identity_keys = {
            "platform", "deviceid", "board", "boardname", "board_name",
            "product", "productname", "model", "devicemodel", "hardware",
        }
        parts = [extra_output]
        for key, value in data.items():
            if (key.lower() in identity_keys or key.lower() in {"firmwareversion", "cpu_model"}
                    or key.lower().endswith(("_platform", "_deviceid", "_board", "_boardname", "_product", "_productname", "_model", "_devicemodel", "_hardware", "_firmwareversion"))):
                parts.append(str(value))
        identity = " ".join(parts)
        compact = re.sub(r"[^a-z0-9]", "", identity.lower())

        # Prefer explicit product identifiers. XS2/XS5 firmware prefixes are
        # only a fallback because several original airOS products share them.
        model_aliases = (
            ("nanostationloco2", "NanoStation Loco2"),
            ("nanostationloco5", "NanoStation Loco5"),
            ("loco2", "NanoStation Loco2"),
            ("loco5", "NanoStation Loco5"),
            ("picostation2", "PicoStation 2"),
            ("picostation5", "PicoStation 5"),
            ("powerstation2", "PowerStation 2"),
            ("powerstation5", "PowerStation 5"),
            ("ps2", "PowerStation 2"),
            ("ps5", "PowerStation 5"),
            ("pico2", "PicoStation 2"),
            ("pico5", "PicoStation 5"),
            ("bullet2", "Bullet2"),
            ("bullet5", "Bullet5"),
            ("nanostation2", "NanoStation 2"),
            ("nanostation5", "NanoStation 5"),
            ("ns2", "NanoStation 2"),
            ("ns5", "NanoStation 5"),
        )
        for alias, label in model_aliases:
            if alias in compact:
                data["device_model"] = label
                return

        firmware = str(data.get("firmwareVersion") or "")
        if not firmware:
            firmware_match = re.search(r"(?i)\b(XS[25])\b", identity)
            firmware = firmware_match.group(1) if firmware_match else ""
        if firmware.upper().startswith("XS2") or re.search(r"(?i)\b(?:NS2|XS2)\b", identity):
            data["device_model"] = "NanoStation 2"
        elif firmware.upper().startswith("XS5") or re.search(r"(?i)\b(?:NS5|XS5)\b", identity):
            data["device_model"] = "NanoStation 5"
        # Match the HTTP integration: do not expose a raw platform or board
        # identifier as the device model. If the model is not recognized, the
        # sensor platform uses the shared generic airOS fallback.

    def _post_process(self, data):
        """Normalize keys to the requested System/Ethernet/Wireless structure."""
        # Defensive cleanup: strip metadata blobs that may have leaked through.
        for key in ("device_name", "hostname", "side_devicename", "device_model"):
            val = data.get(key)
            if isinstance(val, str) and (",deviceid=" in val.lower() or ",firmwareversion=" in val.lower() or ",platform=" in val.lower()):
                data[key] = val.split(",")[0].strip() or "AirOS Device"
        # Re-identify if model was corrupted or missing.
        if not data.get("device_model") or data.get("device_model") in {"UBNT", "AirOS Device"}:
            self._identify_device(data)

        data["device_status"] = "Online"

        # Device name: prefer explicit device_name/hostname, fall back to configured.
        name = data.get("device_name") or data.get("hostname") or data.get("side_devicename") or self.device_name
        if name:
            data["device_name"] = name
            data.setdefault("hostname", name)

        # Device ID / MAC
        for k in ("deviceId", "device_id", "deviceid"):
            if data.get(k):
                data.setdefault("device_id", data[k])
                break
        if not data.get("device_id"):
            for k in ("mac", "lan_mac_address", "wlanMac", "wireless_mac"):
                if data.get(k):
                    data["device_id"] = data[k]
                    break

        # Firmware version
        fv = data.get("firmwareVersion") or data.get("firmware_version") or data.get("fwversion")
        if fv:
            data["firmware_version"] = fv

        # Uptime - keep uptime_seconds
        # CPU usage already set
        # System load
        # Parse load from /proc/loadavg if present in uptime probe? we didn't capture; get from uptime command output not stored.
        # We can derive from /proc/loadavg via a probe; add simple parse if we stored it.

        # Memory
        if data.get("mem_total_bytes") is not None:
            data["total_memory_bytes"] = data["mem_total_bytes"]
        if data.get("mem_free_bytes") is not None:
            data["free_memory_bytes"] = data["mem_free_bytes"]

        # Ethernet - map to requested names
        if data.get("ethernet_mac") or data.get("lan_mac_address") or data.get("mac"):
            data["ethernet_mac_address"] = data.get("ethernet_mac") or data.get("lan_mac_address") or data.get("mac")
        if data.get("lan_ip_address") or data.get("ip_address"):
            data.setdefault("lan_ip_address", data.get("ip_address"))
        # Ethernet link status/speed/duplex from mca-status keys
        lookup = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in data.items()}
        def _lk(*names):
            for n in names:
                v = lookup.get(re.sub(r"[^a-z0-9]", "", n.lower()))
                if v not in (None, ""):
                    return v
            return None
        eth_status = _lk("ethstatus", "eth_plugged", "lanplugged", "plugged")
        if eth_status is not None:
            val = str(eth_status).strip().lower()
            if val in {"1", "up", "on", "true", "enabled", "plugged"}:
                data.setdefault("ethernet_link_status", "Connected")
            elif val in {"0", "down", "off", "false", "disabled", "unplugged"}:
                data.setdefault("ethernet_link_status", "Disconnected")
            else:
                data.setdefault("ethernet_link_status", str(eth_status))
        if data.get("ethernet_interface_state") and not data.get("ethernet_link_status"):
            st = str(data["ethernet_interface_state"]).upper()
            data["ethernet_link_status"] = "Connected" if st == "ON" else "Disconnected"

        speed = _lk("ethspeed", "eth_speed", "ethernet_speed", "lan_speed")
        duplex = _lk("ethduplex", "eth_duplex", "ethernet_duplex", "lan_duplex")
        if speed is not None:
            data.setdefault("ethernet_speed", str(speed))
        if duplex is not None:
            data.setdefault("ethernet_duplex", str(duplex))
        subnet = _lk("netmask", "lan_netmask", "ethernet_netmask", "mask")
        if subnet is not None:
            data.setdefault("lan_subnet_mask", str(subnet))

        # Wireless
        if not data.get("wireless_interface"):
            data["wireless_interface"] = "ath0"
        if data.get("wlanMac") and not data.get("wireless_mac_address"):
            data["wireless_mac_address"] = data["wlanMac"]
        if data.get("wireless_mac") and not data.get("wireless_mac_address"):
            data["wireless_mac_address"] = data["wireless_mac"]
        if data.get("wireless_mode"):
            data["wireless_mode"] = str(data["wireless_mode"])
        if data.get("essid"):
            data["ssid"] = data["essid"]
        # Frequency - mca-status gives MHz sometimes as "frequency" or "freq"
        freq = _lk("frequency", "freq", "wlanFrequency")
        if freq is not None and "frequency_mhz" not in data:
            try:
                f = float(freq)
                # if value looks like GHz
                if f < 100:
                    f = f * 1000
                data["frequency_mhz"] = f
            except (TypeError, ValueError):
                data["frequency_mhz"] = freq
        if data.get("frequency") is not None and "frequency_mhz" not in data:
            try:
                f = float(data["frequency"])
                data["frequency_mhz"] = f
            except Exception:
                pass
        chan = _lk("channel", "wlanChannel", "freq_channel")
        if chan is not None:
            data.setdefault("channel", str(chan))
        cw = _lk("channelwidth", "chanbw", "ht", "channel_width")
        if cw is not None:
            data.setdefault("channel_width", str(cw))
        txp = _lk("txpower", "tx_power", "wlanTxPower")
        if txp is not None:
            data.setdefault("tx_power", str(txp))
        # Signal/noise/snr/ccq/rates already normalized
        if data.get("signal") is not None:
            data["signal_strength"] = data["signal"]
        if data.get("noise") is not None:
            data["noise_floor"] = data["noise"]
        # Wireless bytes/errors - map from existing keys
        if data.get("wireless_rx_bytes") is not None:
            data.setdefault("wlan_rx_bytes", data["wireless_rx_bytes"])
        if data.get("wireless_tx_bytes") is not None:
            data.setdefault("wlan_tx_bytes", data["wireless_tx_bytes"])
        if data.get("wireless_rx_errors") is not None:
            data.setdefault("wlan_rx_errors", data["wireless_rx_errors"])
        if data.get("wireless_tx_errors") is not None:
            data.setdefault("wlan_tx_errors", data["wireless_tx_errors"])

        # Ensure ethernet interface name
        data.setdefault("ethernet_interface", "eth0")

        # Keep _system_logs_full for sensor attributes; diagnostics redacts it.

    @staticmethod
    def _update_firmware_upgrade_status(data):
        """Compare supported legacy NanoStation5 firmware with Ubiquiti's published release."""
        # Ubiquiti's published final legacy NanoStation5 release is v4.0.4
        # build 5074. Do not extrapolate this catalog entry to other models.
        data["firmware_upgrade_latest_version"] = "4.0.4.5074"
        data["firmware_upgrade_source"] = "https://ui.com/download/airmax-legacy"

        if data.get("device_model") != "NanoStation 5":
            data["firmware_upgrade"] = "Unknown"
            data["firmware_upgrade_reason"] = "No verified firmware catalog entry for this device model."
            return

        installed = str(data.get("firmwareVersion") or "")
        match = re.search(r"v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?", installed, re.IGNORECASE)
        if not match:
            data["firmware_upgrade"] = "Unknown"
            data["firmware_upgrade_reason"] = "Installed firmware version could not be parsed."
            return

        installed_version = tuple(int(part or 0) for part in match.groups())
        latest_version = (4, 0, 4, 5074)
        data["firmware_upgrade_installed_version"] = installed
        if installed_version < latest_version:
            data["firmware_upgrade"] = "Update available"
            data["firmware_upgrade_reason"] = "A newer published legacy NanoStation5 firmware version exists. Check release notes and upgrade prerequisites before installing."
        elif installed_version == latest_version:
            data["firmware_upgrade"] = "Up to date"
            data["firmware_upgrade_reason"] = "Installed version matches the published legacy NanoStation5 release."
        else:
            data["firmware_upgrade"] = "Unknown"
            data["firmware_upgrade_reason"] = "Installed version is newer than the catalog entry; automatic comparison is inconclusive."

    def _parse_probe(self, name, output, data):
        if not output:
            return

        if name == "uptime":
            match = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", output)
            if match:
                data["uptime_seconds"] = float(match.group(1))
            # /proc/loadavg style: "0.15 0.10 0.05 1/60 1234"
            parts = output.strip().split()
            if len(parts) >= 3:
                try:
                    float(parts[0]); float(parts[1]); float(parts[2])
                    data.setdefault("system_load", f"{parts[0]} {parts[1]} {parts[2]}")
                except ValueError:
                    pass
        elif name == "loadavg":
            parts = output.strip().split()
            if len(parts) >= 3:
                try:
                    float(parts[0]); float(parts[1]); float(parts[2])
                    data["system_load"] = f"{parts[0]} {parts[1]} {parts[2]}"
                except ValueError:
                    pass
        elif name == "meminfo":
            values = {}
            for line in output.splitlines():
                match = re.match(r"^(MemTotal|MemFree|MemAvailable):\s+(\d+)", line)
                if match:
                    values[match.group(1)] = int(match.group(2)) * 1024
            for source, target in (
                ("MemTotal", "mem_total_bytes"),
                ("MemFree", "mem_free_bytes"),
                ("MemAvailable", "mem_available_bytes"),
            ):
                if source in values:
                    data[target] = values[source]

            # Report a single percentage-based RAM sensor. Prefer MemAvailable,
            # which accounts for reclaimable cache; older kernels may only expose
            # MemFree, so use that as a fallback.
            total = data.get("mem_total_bytes")
            available = data.get("mem_available_bytes", data.get("mem_free_bytes"))
            if total and available is not None and total > 0:
                used_percent = (total - available) / total * 100
                data["ram_usage_percent"] = round(max(0.0, min(100.0, used_percent)), 2)
        elif name == "cpu_stat":
            # /proc/stat exposes cumulative CPU time counters. Compare consecutive
            # samples to calculate actual utilisation rather than load average.
            lines = output.splitlines()
            fields = lines[0].split() if lines else []
            if fields and fields[0] == "cpu" and len(fields) >= 5:
                try:
                    counters = [int(value) for value in fields[1:9]]
                except ValueError:
                    counters = []

                if len(counters) >= 4:
                    total = sum(counters)
                    idle = counters[3]
                    if len(counters) >= 5:
                        idle += counters[4]  # Treat I/O wait as idle time.

                    previous = self._previous_cpu_stats
                    self._previous_cpu_stats = (total, idle)
                    if previous is not None:
                        total_delta = total - previous[0]
                        idle_delta = idle - previous[1]
                        if total_delta > 0 and 0 <= idle_delta <= total_delta:
                            data["cpu_usage"] = round(
                                100 * (total_delta - idle_delta) / total_delta, 2
                            )
        elif name == "cpu_top":
            # Some older AirOS builds do not expose usable /proc/stat counters.
            # Fall back to the CPU summary printed by BusyBox top.
            if "cpu_usage" not in data:
                cpu_lines = [
                    line for line in output.splitlines()
                    if re.search(r"\bCPU\s*:", line, re.IGNORECASE)
                ]
                if cpu_lines:
                    values = {
                        label.lower(): float(value)
                        for value, label in re.findall(
                            r"(\d+(?:\.\d+)?)\s*%\s*([a-z]+)",
                            cpu_lines[-1],
                            re.IGNORECASE,
                        )
                    }
                    idle = values.get("idle")
                    if idle is not None:
                        # I/O wait is treated as idle; other reported categories
                        # (user, system, IRQ, softirq, nice) count as busy.
                        io_wait = values.get("io", 0.0)
                        usage = max(0.0, min(100.0, 100.0 - idle - io_wait))
                        data["cpu_usage"] = round(usage, 2)
        elif name == "version":
            # The legacy /etc/version file often contains the full firmware build,
            # even when mca-status does not expose firmwareVersion.
            if re.search(r"(?i)(?:XS[25]|NS[25]|NanoStation)", output) and re.search(r"\d+\.\d+\.\d+", output):
                data.setdefault("firmwareVersion", output.strip().splitlines()[0])
            self._identify_device(data, output)
        elif name == "board":
            # Some firmware exposes model/board identity in this file.
            self._identify_device(data, output)
        elif name == "cpuinfo":
            for line in output.splitlines():
                if ":" in line and line.split(":", 1)[0].strip().lower() in (
                    "system type", "model name", "processor"
                ):
                    value = line.split(":", 1)[1].strip()
                    if value:
                        data["cpu_model"] = value
                        self._identify_device(data)
                        break
        elif name == "ifconfig":
            # Parse each interface separately; order varies by firmware.
            # Legacy airOS commonly uses ath0/wlan0, eth0, and br0.
            blocks = re.split(r"(?m)^(?=[A-Za-z0-9_.:-]+\s+Link encap:)", output)
            for block in blocks:
                heading = re.match(r"^([A-Za-z0-9_.:-]+)\s+Link encap:", block)
                if not heading:
                    continue
                interface = heading.group(1).lower()
                is_wireless = interface.startswith(("wlan", "ath"))
                is_ethernet = interface.startswith(("eth", "br"))
                is_ppp = interface.startswith("ppp")
                if not (is_wireless or is_ethernet or is_ppp):
                    continue
                prefix = "wireless" if is_wireless else ("ppp" if is_ppp else "ethernet")
                mac = re.search(r"(?:HWaddr|ether)\s+([0-9A-Fa-f:]{17})", block)
                if mac:
                    data.setdefault(f"{prefix}_mac", mac.group(1))
                    if is_ethernet:
                        data.setdefault("mac", mac.group(1))
                        data.setdefault("lan_mac_address", mac.group(1))
                    if is_wireless:
                        data.setdefault("wlanMac", mac.group(1))
                ip = re.search(r"inet addr:([0-9.]+)", block)
                mask = re.search(r"Mask:([0-9.]+)", block)
                if not ip:
                    ip = re.search(r"\binet ([0-9.]+)", block)
                if not mask:
                    mask = re.search(r"netmask ([0-9.]+)", block)
                if ip:
                    data.setdefault("ip_address", ip.group(1))
                    if is_ethernet:
                        data.setdefault("lan_ip_address", ip.group(1))
                    if is_ppp:
                        data.setdefault("ppp_ip", ip.group(1))
                if mask and is_ethernet:
                    data.setdefault("lan_subnet_mask", mask.group(1))
                if is_ethernet and not data.get("ethernet_interface"):
                    data["ethernet_interface"] = heading.group(1)
                if is_wireless and not data.get("wireless_interface"):
                    data["wireless_interface"] = heading.group(1)

                flags = re.search(r"<([^>]+)>", block)
                if flags:
                    state = "up" if "UP" in flags.group(1).split(",") else "down"
                    data.setdefault(f"{prefix}_interface_state", state)
                    if is_ethernet:
                        data["ethernet_interface_state"] = "ON" if state == "up" else "OFF"
                elif re.search(r"(?m)^\s*UP(?:\s|$)", block):
                    data.setdefault(f"{prefix}_interface_state", "up")
                    if is_ethernet:
                        data["ethernet_interface_state"] = "ON"
                elif re.search(r"(?m)^\s*DOWN(?:\s|$)", block):
                    data.setdefault(f"{prefix}_interface_state", "down")
                    if is_ethernet:
                        data["ethernet_interface_state"] = "OFF"

        elif name == "netdev":
            # Prefer physical interfaces to bridge aliases, avoiding br0 counters
            # being mislabeled as the physical Ethernet port when eth0 is present.
            counters = {}
            for line in output.splitlines():
                if ":" not in line:
                    continue
                interface, stats = line.split(":", 1)
                interface = interface.strip().lower()
                values = stats.split()
                if len(values) < 16:
                    # Some old kernels have fewer fields; pad.
                    values = values + ["0"] * (16 - len(values))
                if interface.startswith(("wlan", "ath")):
                    prefix, priority = "wireless", 2
                elif interface.startswith("ppp"):
                    prefix, priority = "ppp", 2
                elif interface.startswith("eth"):
                    prefix, priority = "ethernet", 2
                elif interface.startswith("br"):
                    prefix, priority = "ethernet", 1
                else:
                    continue
                try:
                    rx_bytes = int(values[0])
                    rx_packets = int(values[1])
                    rx_errors = int(values[2])
                    rx_dropped = int(values[3])
                    tx_bytes = int(values[8])
                    tx_packets = int(values[9])
                    tx_errors = int(values[10])
                    tx_dropped = int(values[11])
                except (TypeError, ValueError, IndexError):
                    _LOGGER.debug("Skipping malformed /proc/net/dev row: %s", line)
                    continue
                previous = counters.get(prefix)
                if previous is None or priority > previous[0]:
                    counters[prefix] = (
                        priority, rx_bytes, rx_packets, rx_errors, rx_dropped,
                        tx_bytes, tx_packets, tx_errors, tx_dropped,
                    )
            for prefix, values in counters.items():
                (_, rx_bytes, rx_packets, rx_errors, rx_dropped,
                 tx_bytes, tx_packets, tx_errors, tx_dropped) = values
                data[f"{prefix}_rx_bytes"] = rx_bytes
                data[f"{prefix}_tx_bytes"] = tx_bytes
                if prefix == "ethernet":
                    data["lan_rx_packets"] = rx_packets
                    data["lan_rx_errors"] = rx_errors
                    data["lan_rx_dropped"] = rx_dropped
                    data["lan_tx_packets"] = tx_packets
                    data["lan_tx_errors"] = tx_errors
                    data["lan_tx_dropped"] = tx_dropped
                elif prefix == "wireless":
                    data["wireless_rx_packets"] = rx_packets
                    data["wireless_rx_errors"] = rx_errors
                    data["wireless_rx_dropped"] = rx_dropped
                    data["wireless_tx_packets"] = tx_packets
                    data["wireless_tx_errors"] = tx_errors
                    data["wireless_tx_dropped"] = tx_dropped
                elif prefix == "ppp":
                    data["ppp_rx_bytes"] = rx_bytes
                    data["ppp_rx_packets"] = rx_packets
                    data["ppp_rx_errors"] = rx_errors
                    data["ppp_tx_bytes"] = tx_bytes
                    data["ppp_tx_packets"] = tx_packets
                    data["ppp_tx_errors"] = tx_errors
        elif name == "system_cfg":
            for line in output.splitlines():
                if "=" not in line:
                    continue
                key, value = line.strip().split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if not value:
                    continue
                if key in {"resolv.host.1.name", "host.hostname", "hostname"}:
                    data.setdefault("device_name", value)
                    data.setdefault("hostname", value)
                elif key in {"radio.1.mode", "wlan.1.mode", "wireless.1.mode"}:
                    data.setdefault("wireless_mode", value)
                elif key in {"wireless.1.ssid", "wlan.1.ssid", "ssid"}:
                    data.setdefault("essid", value)
                elif key in {"radio.1.freq", "wireless.1.freq"}:
                    data.setdefault("frequency_mhz_cfg", value)
                elif key in {"radio.1.chanbw", "wireless.1.chanbw"}:
                    data.setdefault("channel_width", value)
                elif key in {"radio.1.txpower", "wireless.1.txpower"}:
                    data.setdefault("tx_power", value)
                elif key in {"radio.countrycode", "radio.1.countrycode"}:
                    data.setdefault("country_code", value)
        elif name == "uname":
            value = output.strip().splitlines()[0].strip() if output.strip() else ""
            if value:
                data["kernel_version"] = value
        elif name == "free":
            # BusyBox free output varies; capture Mem row.
            for line in output.splitlines():
                parts = line.split()
                if not parts:
                    continue
                if parts[0].lower().startswith("mem"):
                    nums = [p for p in parts[1:] if p.isdigit()]
                    if len(nums) >= 2:
                        # free may report kB or bytes depending on flags/version.
                        # Heuristic: if value looks like kB (common), convert to bytes.
                        total = int(nums[0])
                        used = int(nums[1]) if len(nums) > 1 else None
                        free_mem = int(nums[2]) if len(nums) > 2 else None
                        # If total is small (< 10^7) assume kB.
                        factor = 1024 if total < 10_000_000 else 1
                        data.setdefault("mem_total_bytes", total * factor)
                        if free_mem is not None:
                            data.setdefault("mem_free_bytes", free_mem * factor)
                        if used is not None and total:
                            data.setdefault("ram_usage_percent", round(max(0.0, min(100.0, used / total * 100)), 2))
                    break
        elif name == "date":
            value = output.strip().splitlines()[0].strip() if output.strip() else ""
            if value:
                data["system_date_time"] = value
        elif name == "ps":
            lines = [l for l in output.splitlines() if l.strip()]
            # Exclude header if present.
            count = 0
            for line in lines:
                if line.strip().lower().startswith(("pid", "  pid")):
                    continue
                count += 1
            if count > 0:
                data["running_processes"] = count
        elif name == "logread":
            lines = [l.rstrip() for l in output.splitlines() if l.strip()]
            if lines:
                # Keep a compact tail for state; full text in attribute via post_process.
                tail = lines[-10:]
                data["system_logs"] = "\n".join(tail)[-1000:]
                data["_system_logs_full"] = "\n".join(lines)[-4000:]
        elif name == "df":
            lines = [l.rstrip() for l in output.splitlines() if l.strip()]
            if lines:
                data["storage_usage"] = "\n".join(lines[-8:])[-1000:]
        elif name == "mount":
            lines = [l.rstrip() for l in output.splitlines() if l.strip()]
            if lines:
                data["filesystem_mounts"] = "\n".join(lines[-12:])[-1000:]
        elif name == "route":
            lines = [l.rstrip() for l in output.splitlines() if l.strip()]
            if lines:
                data["routing_table"] = "\n".join(lines[-12:])[-1000:]
        elif name == "arp":
            lines = [l.rstrip() for l in output.splitlines() if l.strip()]
            if lines:
                data["arp_table"] = "\n".join(lines[-12:])[-1000:]
        elif name == "brctl":
            lines = [l.rstrip() for l in output.splitlines() if l.strip()]
            if lines:
                data["bridge_information"] = "\n".join(lines[-12:])[-1000:]
        elif name == "iwconfig":
            text_out = output.strip()
            if text_out and "no wireless extensions" not in text_out.lower():
                data.setdefault("wireless_interface", "ath0")
                mac = re.search(r"(?:Access Point|HWaddr|ether)\s*[:=]?\s*([0-9A-Fa-f:]{17})", text_out)
                # Access Point is AP MAC; HWaddr is interface MAC.
                hw = re.search(r"HWaddr\s+([0-9A-Fa-f:]{17})", text_out)
                if hw:
                    data.setdefault("wlanMac", hw.group(1))
                    data.setdefault("wireless_mac", hw.group(1))
                essid = re.search(r'ESSID:"([^"]*)"', text_out)
                if essid:
                    data.setdefault("essid", essid.group(1))
                freq = re.search(r"Frequency[:=]([0-9.]+)\s*GHz", text_out)
                if freq:
                    try:
                        data.setdefault("frequency", float(freq.group(1)) * 1000)
                    except ValueError:
                        pass
                elif re.search(r"Frequency[:=]([0-9.]+)\s*MHz", text_out):
                    m = re.search(r"Frequency[:=]([0-9.]+)\s*MHz", text_out)
                    try:
                        data.setdefault("frequency", float(m.group(1)))
                    except ValueError:
                        pass
                channel = re.search(r"Channel[:=]([0-9]+)", text_out)
                if channel:
                    data.setdefault("channel", int(channel.group(1)))
                txpower = re.search(r"Tx-Power[:=]([0-9]+)", text_out, re.IGNORECASE)
                if txpower:
                    data.setdefault("tx_power", txpower.group(1) + " dBm")
                rate = re.search(r"Rate[:=]([0-9.]+)\s*Mb/s", text_out)
                if rate:
                    try:
                        data.setdefault("wlanTxRate", float(rate.group(1)))
                    except ValueError:
                        pass
                # Bit Rate may appear twice (tx/rx) on some builds; capture all.
                rates = re.findall(r"(?:Bit Rate|Rate)[:=]([0-9.]+)\s*Mb/s", text_out)
                if len(rates) >= 1:
                    try:
                        data.setdefault("wlanTxRate", float(rates[0]))
                    except ValueError:
                        pass
                if len(rates) >= 2:
                    try:
                        data.setdefault("wlanRxRate", float(rates[1]))
                    except ValueError:
                        pass
                mode = re.search(r"Mode:([^\s]+)", text_out)
                if mode:
                    data.setdefault("wireless_mode", mode.group(1))
        elif name == "athstats":
            text_out = output.strip()
            if text_out and "not found" not in text_out.lower():
                data["radio_statistics"] = "\n".join(text_out.splitlines()[-20:])[-1500:]
                retries = re.search(r"(?im)^\s*(?:tx retries|data retries|long retries)\s*[:=]?\s*(\d+)", text_out)
                if retries:
                    data.setdefault("wireless_retries", int(retries.group(1)))
        elif name == "wstalist":
            text_out = output.strip()
            if text_out and "not found" not in text_out.lower():
                data["connected_stations"] = "\n".join(text_out.splitlines()[-20:])[-1500:]
                # Count MAC-like entries as stations if possible.
                macs = re.findall(r"[0-9A-Fa-f:]{17}", text_out)
                if macs:
                    data.setdefault("connected_station_count", len(set(macs)))
        elif name == "iwlist_scan":
            text_out = output.strip()
            if text_out and "not found" not in text_out.lower():
                # Summarize: count cells and keep tail.
                cells = len(re.findall(r"Cell \d+", text_out))
                data["available_networks_count"] = cells
                data["available_networks"] = "\n".join(text_out.splitlines()[-30:])[-1500:]