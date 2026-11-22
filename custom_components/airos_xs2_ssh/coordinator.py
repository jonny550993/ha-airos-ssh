import logging
import re
from datetime import timedelta

import asyncssh
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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


def _first_line(text: str) -> str:
    for line in _to_text(text).splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _parse_kv_output(output: str) -> dict:
    data = {}
    for line in _to_text(output).splitlines():
        if "=" in line:
            key, value = line.strip().split("=", 1)
            data[key.strip()] = value.strip()
    return data


class AiRXS2Coordinator(DataUpdateCoordinator):
    """Poll a legacy Ubiquiti NanoStation5 over SSH."""

    def __init__(self, hass: HomeAssistant, host, username, password, name):
        self.host = host
        self.username = username
        self.password = password
        self.device_name = name

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{name}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _run_command(self, conn, command: str) -> str:
        async with conn.create_process(command) as proc:
            stdout = await proc.stdout.read()
            stderr = await proc.stderr.read()
            await proc.wait()
        out = _to_text(stdout).strip()
        err = _to_text(stderr).strip()
        return out if out else err

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
                commands = {
                    "mca_status": "mca-status",
                    "system_cfg": "cat /tmp/system.cfg",
                    "version": "cat /etc/version",
                    "uname": "uname -a",
                    "uptime": "uptime",
                    "top": "top -b -n1 | head -n 5",
                    "free": "free",
                    "ps": "ps",
                    "date": "date",
                    "logread": "logread | tail -n 50",
                    "df": "df -h",
                    "mount": "mount",
                    "ifconfig_eth0": "ifconfig eth0",
                    "ifconfig_br0": "ifconfig br0",
                    "ifconfig": "ifconfig",
                    "proc_net_dev": "cat /proc/net/dev",
                    "route": "route -n",
                    "arp": "arp -n",
                    "brctl": "brctl show",
                    "iwconfig_ath0": "iwconfig ath0",
                    "athstats": "athstats",
                    "wstalist": "wstalist",
                    "iwlist_scan": "iwlist ath0 scan | head -n 120",
                }

                results = {}
                for key, cmd in commands.items():
                    try:
                        results[key] = await self._run_command(conn, cmd)
                    except Exception as err:
                        _LOGGER.debug("Command failed (%s): %s", cmd, err)
                        results[key] = ""

                return self._parse_results(results)

        except Exception as err:
            raise UpdateFailed(f"SSH error: {err}") from err

    def _parse_results(self, r: dict) -> dict:
        data = {}
        mca = _parse_kv_output(r.get("mca_status", ""))

        # 1. System
        data["device_status"] = "ok" if mca else "unavailable"
        data["device_status_raw"] = r.get("mca_status", "")
        data["device_name"] = self._parse_device_name(r.get("system_cfg", ""), mca)
        data["device_model"] = mca.get("deviceName") or mca.get("platform") or mca.get("board.hwaddr") or "NanoStation5 Legacy"
        data["device_id"] = mca.get("deviceId") or mca.get("device_id") or mca.get("apMac") or ""
        data["firmware_version"] = _first_line(r.get("version", "")) or mca.get("firmwareVersion", "")
        data["kernel_version"] = _first_line(r.get("uname", ""))
        data["uptime"] = _first_line(r.get("uptime", ""))
        self._parse_cpu_load(r.get("uptime", ""), r.get("top", ""), data)
        self._parse_free(r.get("free", ""), data)
        data["running_processes"] = self._count_lines(r.get("ps", ""), header=True)
        data["running_processes_raw"] = r.get("ps", "")
        data["system_datetime"] = _first_line(r.get("date", ""))
        data["system_logs"] = self._tail_summary(r.get("logread", ""))
        data["system_logs_raw"] = r.get("logread", "")
        data["storage_usage"] = self._df_summary(r.get("df", ""))
        data["storage_usage_raw"] = r.get("df", "")
        data["filesystem_mounts"] = self._count_lines(r.get("mount", ""), header=False)
        data["filesystem_mounts_raw"] = r.get("mount", "")

        # 2. Ethernet
        eth0 = r.get("ifconfig_eth0", "")
        br0 = r.get("ifconfig_br0", "")
        proc_dev = r.get("proc_net_dev", "")
        data["eth_interface"] = "eth0" if "eth0" in eth0 else ""
        data["eth_mac"] = self._parse_mac(eth0) or mca.get("lanMac", "")
        data["lan_ip"] = self._parse_ip(br0) or self._parse_ip(eth0)
        data["lan_subnet"] = self._parse_mask(br0) or self._parse_mask(eth0)
        self._parse_eth_link(mca, eth0, data)
        self._parse_proc_net_dev(proc_dev, "eth0", "eth", data)
        self._parse_ifconfig_counters(eth0, "eth", data)
        data["routing_table"] = self._count_lines(r.get("route", ""), header=True)
        data["routing_table_raw"] = r.get("route", "")
        data["arp_table"] = self._count_lines(r.get("arp", ""), header=True)
        data["arp_table_raw"] = r.get("arp", "")
        data["bridge_info"] = self._count_lines(r.get("brctl", ""), header=True)
        data["bridge_info_raw"] = r.get("brctl", "")

        # 3. Wireless
        iw = r.get("iwconfig_ath0", "")
        data["wlan_interface"] = "ath0" if "ath0" in iw else ""
        data["wlan_mac"] = self._parse_iw_mac(iw) or mca.get("wlanOpmode", "") and mca.get("apMac", "") or mca.get("apMac", "")
        # prefer wlanHwAddr/wlanMac-like keys if present
        for k in ("wlanMac", "wlanHwAddr", "ath0_hwaddr", "apMac"):
            if mca.get(k):
                data["wlan_mac"] = mca.get(k)
                break
        self._parse_iwconfig(iw, mca, data)
        self._parse_wireless_mca(mca, data)
        self._parse_athstats(r.get("athstats", ""), data)
        self._parse_wstalist(r.get("wstalist", ""), data)
        data["available_networks"] = self._count_iwlist_scan(r.get("iwlist_scan", ""))
        data["available_networks_raw"] = r.get("iwlist_scan", "")

        # Normalize empty strings to None for cleaner sensors
        for k, v in list(data.items()):
            if isinstance(v, str):
                v = v.strip()
                data[k] = v if v else None
        return data

    @staticmethod
    def _parse_device_name(system_cfg: str, mca: dict) -> str:
        for line in _to_text(system_cfg).splitlines():
            if line.startswith("resolv.host.1.name="):
                return line.split("=", 1)[1].strip()
            if line.startswith("host.hostname="):
                return line.split("=", 1)[1].strip()
        return mca.get("deviceName") or mca.get("hostName") or ""

    @staticmethod
    def _parse_cpu_load(uptime_out: str, top_out: str, data: dict):
        load_match = re.search(r"load average[s]?:\s*([0-9.]+)[, ]+([0-9.]+)[, ]+([0-9.]+)", uptime_out)
        if load_match:
            data["system_load"] = f"{load_match.group(1)}, {load_match.group(2)}, {load_match.group(3)}"
        else:
            data["system_load"] = None

        cpu = None
        for line in _to_text(top_out).splitlines():
            m = re.search(r"CPU:.*?([0-9.]+)%\s*idle", line, re.IGNORECASE)
            if m:
                cpu = round(max(0.0, 100.0 - float(m.group(1))), 2)
                break
            m = re.search(r"([0-9.]+)\s*%?\s*id", line, re.IGNORECASE)
            if m and "cpu" in line.lower():
                cpu = round(max(0.0, 100.0 - float(m.group(1))), 2)
                break
        data["cpu_usage"] = cpu

    @staticmethod
    def _parse_free(free_out: str, data: dict):
        total = free = None
        for line in _to_text(free_out).splitlines():
            parts = line.split()
            if not parts:
                continue
            if parts[0].lower().startswith("mem"):
                nums = [int(p) for p in parts[1:] if p.isdigit()]
                if len(nums) >= 2:
                    total, used, free_mem = (nums + [None, None, None])[:3]
                    # busybox free: total used free shared buffers
                    data["memory_total"] = total
                    data["memory_free"] = free_mem
                    return
        data["memory_total"] = None
        data["memory_free"] = None

    @staticmethod
    def _count_lines(text: str, header=False) -> int | None:
        lines = [l for l in _to_text(text).splitlines() if l.strip()]
        if not lines:
            return None
        if header and len(lines) > 0:
            return max(0, len(lines) - 1)
        return len(lines)

    @staticmethod
    def _tail_summary(text: str) -> str | None:
        lines = [l.strip() for l in _to_text(text).splitlines() if l.strip()]
        if not lines:
            return None
        return f"{len(lines)} entries"

    @staticmethod
    def _df_summary(text: str) -> str | None:
        lines = [l for l in _to_text(text).splitlines() if l.strip()]
        if len(lines) < 2:
            return None
        # return summary of root or last data line
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 5 and parts[-1] in ("/", "/tmp", "/etc"):
                return f"{parts[-1]} {parts[-2]} used"
        parts = lines[-1].split()
        if len(parts) >= 5:
            return f"{parts[-1]} {parts[-2]} used"
        return f"{len(lines)-1} filesystems"

    @staticmethod
    def _parse_mac(text: str) -> str | None:
        m = re.search(r"HWaddr\s+([0-9A-Fa-f:]{17})", text)
        if m:
            return m.group(1).upper()
        m = re.search(r"ether\s+([0-9A-Fa-f:]{17})", text)
        return m.group(1).upper() if m else None

    @staticmethod
    def _parse_ip(text: str) -> str | None:
        m = re.search(r"inet addr:([0-9.]+)", text)
        if m:
            return m.group(1)
        m = re.search(r"\binet\s+([0-9.]+)", text)
        return m.group(1) if m else None

    @staticmethod
    def _parse_mask(text: str) -> str | None:
        m = re.search(r"Mask:([0-9.]+)", text)
        if m:
            return m.group(1)
        m = re.search(r"netmask\s+([0-9.]+)", text)
        return m.group(1) if m else None

    @staticmethod
    def _parse_eth_link(mca: dict, eth0: str, data: dict):
        plugged = mca.get("lan plugged") or mca.get("lanPlugged") or mca.get("plugged")
        if plugged is not None:
            data["eth_link_status"] = "up" if str(plugged).lower() in ("1", "true", "yes", "up") else "down"
        else:
            data["eth_link_status"] = "up" if "RUNNING" in eth0 else ("down" if eth0 else None)
        data["eth_speed"] = mca.get("lanSpeed") or mca.get("eth0.speed")
        data["eth_duplex"] = mca.get("lanDuplex") or mca.get("eth0.duplex")

    @staticmethod
    def _parse_proc_net_dev(proc_dev: str, iface: str, prefix: str, data: dict):
        for line in _to_text(proc_dev).splitlines():
            if ":" not in line:
                continue
            name, rest = line.split(":", 1)
            if name.strip() != iface:
                continue
            vals = rest.split()
            if len(vals) >= 16:
                data[f"{prefix}_rx_bytes"] = _number(vals[0])
                data[f"{prefix}_rx_packets_proc"] = _number(vals[1])
                data[f"{prefix}_rx_errors_proc"] = _number(vals[2])
                data[f"{prefix}_rx_dropped"] = _number(vals[3])
                data[f"{prefix}_tx_bytes"] = _number(vals[8])
                data[f"{prefix}_tx_packets_proc"] = _number(vals[9])
                data[f"{prefix}_tx_errors_proc"] = _number(vals[10])
                data[f"{prefix}_tx_dropped"] = _number(vals[11])
            return

    @staticmethod
    def _parse_ifconfig_counters(text: str, prefix: str, data: dict):
        rx_packets = re.search(r"RX packets:(\d+)", text)
        tx_packets = re.search(r"TX packets:(\d+)", text)
        rx_errors = re.search(r"RX packets:\d+.*?errors:(\d+)", text)
        tx_errors = re.search(r"TX packets:\d+.*?errors:(\d+)", text)
        rx_dropped = re.search(r"RX packets:\d+.*?dropped:(\d+)", text)
        tx_dropped = re.search(r"TX packets:\d+.*?dropped:(\d+)", text)
        rx_bytes = re.search(r"RX bytes:(\d+)", text)
        tx_bytes = re.search(r"TX bytes:(\d+)", text)
        # prefer proc values if already set
        if data.get(f"{prefix}_rx_packets_proc") is None and rx_packets:
            data[f"{prefix}_rx_packets"] = int(rx_packets.group(1))
        else:
            data[f"{prefix}_rx_packets"] = data.pop(f"{prefix}_rx_packets_proc", None) or (int(rx_packets.group(1)) if rx_packets else None)
        if data.get(f"{prefix}_tx_packets_proc") is None and tx_packets:
            data[f"{prefix}_tx_packets"] = int(tx_packets.group(1))
        else:
            data[f"{prefix}_tx_packets"] = data.pop(f"{prefix}_tx_packets_proc", None) or (int(tx_packets.group(1)) if tx_packets else None)
        if data.get(f"{prefix}_rx_errors_proc") is None and rx_errors:
            data[f"{prefix}_rx_errors"] = int(rx_errors.group(1))
        else:
            data[f"{prefix}_rx_errors"] = data.pop(f"{prefix}_rx_errors_proc", None) or (int(rx_errors.group(1)) if rx_errors else None)
        if data.get(f"{prefix}_tx_errors_proc") is None and tx_errors:
            data[f"{prefix}_tx_errors"] = int(tx_errors.group(1))
        else:
            data[f"{prefix}_tx_errors"] = data.pop(f"{prefix}_tx_errors_proc", None) or (int(tx_errors.group(1)) if tx_errors else None)
        if data.get(f"{prefix}_rx_dropped") is None and rx_dropped:
            data[f"{prefix}_rx_dropped"] = int(rx_dropped.group(1))
        if data.get(f"{prefix}_tx_dropped") is None and tx_dropped:
            data[f"{prefix}_tx_dropped"] = int(tx_dropped.group(1))
        if data.get(f"{prefix}_rx_bytes") is None and rx_bytes:
            data[f"{prefix}_rx_bytes"] = int(rx_bytes.group(1))
        if data.get(f"{prefix}_tx_bytes") is None and tx_bytes:
            data[f"{prefix}_tx_bytes"] = int(tx_bytes.group(1))

    @staticmethod
    def _parse_iw_mac(text: str) -> str | None:
        m = re.search(r"Access Point:\s*([0-9A-Fa-f:]{17})", text)
        if m and m.group(1) != "00:00:00:00:00:00":
            return None
        m = re.search(r"HWaddr\s+([0-9A-Fa-f:]{17})", text)
        return m.group(1).upper() if m else None

    @staticmethod
    def _parse_iwconfig(iw: str, mca: dict, data: dict):
        ssid = re.search(r'ESSID:"?([^"\n]+)"?', iw)
        freq = re.search(r"Frequency[:=]([0-9.]+)\s*GHz", iw)
        channel = re.search(r"Channel[:=]([0-9]+)", iw)
        txpower = re.search(r"Tx-Power[:=]([0-9]+)\s*dBm", iw) or re.search(r"Tx-Power=([0-9]+)", iw)
        rate = re.search(r"Bit Rate[:=]([0-9.]+)\s*Mb/s", iw)
        rates = re.findall(r"([0-9.]+)\s*Mb/s", iw)
        mode = re.search(r"Mode:([A-Za-z-]+)", iw)
        ap = re.search(r"Access Point:\s*([0-9A-Fa-f:]{17})", iw)

        data["ssid"] = ssid.group(1).strip() if ssid else mca.get("essid")
        if freq:
            data["frequency"] = round(float(freq.group(1)) * 1000, 0)
        else:
            data["frequency"] = _number(mca.get("freq"))
        data["channel"] = int(channel.group(1)) if channel else _number(mca.get("channel"))
        data["channel_width"] = mca.get("chanbw") or mca.get("channelWidth")
        data["tx_power"] = int(txpower.group(1)) if txpower else _number(mca.get("txpower"))
        data["wireless_mode"] = mode.group(1) if mode else mca.get("wlanOpmode") or mca.get("ieeemode")
        if rates:
            data["tx_data_rate"] = float(rates[0])
            data["rx_data_rate"] = float(rates[1]) if len(rates) > 1 else float(rates[0])
        else:
            data["tx_data_rate"] = _number(mca.get("wlanTxRate"))
            data["rx_data_rate"] = _number(mca.get("wlanRxRate"))
        if not data.get("wlan_mac") and ap and ap.group(1) != "00:00:00:00:00:00":
            # Access Point is AP MAC; interface MAC may differ, keep as fallback only
            pass

    @staticmethod
    def _parse_wireless_mca(mca: dict, data: dict):
        signal = _number(mca.get("signal"))
        noise = _number(mca.get("noise"))
        ccq = _number(mca.get("ccq"))
        data["signal_strength"] = signal
        data["noise_floor"] = noise
        data["snr"] = (signal - noise) if signal is not None and noise is not None else None
        data["ccq"] = round(ccq / 10, 1) if ccq is not None else None
        data["wlan_rx_bytes"] = _number(mca.get("wlanRxBytes"))
        data["wlan_tx_bytes"] = _number(mca.get("wlanTxBytes"))
        data["wlan_rx_errors"] = _number(mca.get("wlanRxErrors"))
        data["wlan_tx_errors"] = _number(mca.get("wlanTxErrors"))

    @staticmethod
    def _parse_athstats(text: str, data: dict):
        if not text.strip():
            data["wireless_retries"] = None
            data["radio_statistics"] = None
            data["radio_statistics_raw"] = None
            return
        retries = re.search(r"tx failed due to too many retries\s*[:=]?\s*(\d+)", text, re.IGNORECASE)
        if not retries:
            retries = re.search(r"retries\s*[:=]?\s*(\d+)", text, re.IGNORECASE)
        data["wireless_retries"] = int(retries.group(1)) if retries else None
        lines = [l for l in text.splitlines() if l.strip()]
        data["radio_statistics"] = f"{len(lines)} lines"
        data["radio_statistics_raw"] = text

    @staticmethod
    def _parse_wstalist(text: str, data: dict):
        if not text.strip():
            data["connected_stations"] = 0
            data["connected_stations_raw"] = None
            return
        macs = re.findall(r"([0-9A-Fa-f:]{17})", text)
        data["connected_stations"] = len(set(macs)) if macs else len([l for l in text.splitlines() if l.strip()])
        data["connected_stations_raw"] = text

    @staticmethod
    def _count_iwlist_scan(text: str) -> int | None:
        if not text.strip():
            return None
        cells = re.findall(r"Cell\s+\d+\s+-", text)
        if cells:
            return len(cells)
        essids = re.findall(r"ESSID:", text)
        return len(essids) if essids else None
