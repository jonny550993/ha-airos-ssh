from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass

from homeassistant.helpers import device_registry as dr, entity_registry as er

from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import DOMAIN, device_identifier

import re



BASE_SENSORS = {

    "signal": ("Signal Strength", "dBm"),

    "noise": ("Noise Floor", "dBm"),

    "ccq": ("CCQ", "%"),

    "snr": ("SNR", "dB"),

    "wlanTxRate": ("TX Data Rate", "Mbit/s"),

    "wlanRxRate": ("RX Data Rate", "Mbit/s"),

}



OPTIONAL_SENSORS = {
    "essid": ("SSID", None),
    "ssid": ("SSID", None),
    "frequency": ("Frequency", "MHz"),
    "frequency_mhz": ("Frequency", "MHz"),
    "channel": ("Channel", None),
    "channel_width": ("Channel Width", None),
    "tx_power": ("TX Power", None),
    "signal_strength": ("Signal Strength", "dBm"),
    "noise_floor": ("Noise Floor", "dBm"),
    "wireless_interface": ("Wireless Interface", None),
    "wireless_mac_address": ("Wireless MAC Address", None),
    "wireless_retries": ("Wireless Retries", None),
    "connected_stations": ("Connected Stations", None),
    "radio_statistics": ("Radio Statistics", None),
    "available_networks": ("Available Networks", None),
    "wlanMac": ("Wireless MAC Address", None),
    "lan_ip_address": ("LAN IP Address", None),
    "lan_mac_address": ("Ethernet MAC Address", None),
    "ethernet_interface_state": ("Ethernet Link Status", None),
    "wireless_interface_state": ("Wireless Interface State", None),
    "wireless_mac": ("Wireless MAC Address", None),
    "mac": ("Device MAC Address", None),
    "mode": ("Wireless Mode", None),
    "hostname": ("Hostname", None),
    "uptime_seconds": ("Uptime", "s"),
    "ip_address": ("Device IP Address", None),
    "cpu_model": ("CPU Model", None),
    "cpu_usage": ("CPU Usage", "%"),
    "firmware_upgrade": ("Firmware Upgrade", None),
    "apmac": ("AP MAC", None), "cfg_crc": ("Config CRC", None),
    "device_model": ("Device Model", None), "distance": ("Distance", None),
    "ack_timeout": ("ACK Timeout", None), "latitude": ("Latitude", None),
    "longitude": ("Longitude", None), "radio_date_time": ("Radio Date and Time", None),
    "ppp_ip": ("PPP IP Address", None), "ppp_rx_errors": ("PPP Receive Errors", None),
    "ppp_rx_bytes": ("PPP Received Data", "B"), "ppp_rx_packets": ("PPP Received Packets", None),
    "ppp_tx_errors": ("PPP Transmit Errors", None), "ppp_tx_bytes": ("PPP Transmitted Data", "B"),
    "ppp_tx_packets": ("PPP Transmitted Packets", None),
    "ram_usage_percent": ("RAM Usage", "%"),
    "ethernet_rx_bytes": ("RX Bytes", "B"),
    "ethernet_tx_bytes": ("TX Bytes", "B"),
    "lan_rx_errors": ("RX Errors", None),
    "lan_rx_packets": ("RX Packets", None),
    "lan_tx_errors": ("TX Errors", None),
    "lan_tx_packets": ("TX Packets", None),
    "wireless_rx_bytes": ("Wireless RX Bytes", "B"),
    "wireless_tx_bytes": ("Wireless TX Bytes", "B"),
    "wlan_rx_bytes": ("Wireless RX Bytes", "B"),
    "wlan_tx_bytes": ("Wireless TX Bytes", "B"),
    "wlan_rx_errors": ("Wireless RX Errors", None),
    "wlan_tx_errors": ("Wireless TX Errors", None),
    "kernel_version": ("Kernel Version", None),
    "system_load": ("System Load", None),
    "total_memory_bytes": ("Total Memory", "B"),
    "free_memory_bytes": ("Free Memory", "B"),
    "running_processes": ("Running Processes", None),
    "system_date_time": ("System Date/Time", None),
    "system_logs": ("System Logs", None),
    "storage_usage": ("Storage Usage", None),
    "filesystem_mounts": ("Filesystem Mounts", None),
    "ethernet_interface": ("Ethernet Interface", None),
    "ethernet_mac_address": ("Ethernet MAC Address", None),
    "lan_subnet_mask": ("Subnet Mask", None),
    "ethernet_link_status": ("Ethernet Link Status", None),
    "ethernet_speed": ("Ethernet Speed", None),
    "ethernet_duplex": ("Ethernet Duplex", None),
    "lan_rx_dropped": ("RX Dropped Packets", None),
    "lan_tx_dropped": ("TX Dropped Packets", None),
    "routing_table": ("Routing Table", None),
    "arp_table": ("ARP Table", None),
    "bridge_information": ("Bridge Information", None),
}



DEVICE_METADATA = {

    "deviceId": ("Device ID", None),

    "firmwareVersion": ("Firmware Version", None),

    "platform": ("Platform", None),

    "deviceIp": ("Configured Device IP Address", None),

}





def _parse_device_name(raw_name):

    """Split comma-separated AirOS metadata out of the device display name."""

    parts = [part.strip() for part in raw_name.split(",")]

    metadata = {}

    known_keys = {key.lower(): key for key in DEVICE_METADATA}



    # Metadata keys can vary in capitalization between AirOS versions.

    # Match known keys case-insensitively and keep only the clean device name.

    for part in parts[1:]:

        if "=" not in part:

            continue

        key, value = part.split("=", 1)

        key = key.strip()

        value = value.strip()

        canonical_key = known_keys.get(key.lower())

        if canonical_key and value:

            metadata[canonical_key] = value



    display_name = parts[0] or "AirOS Device"

    return display_name, metadata





SENSOR_NAME_OVERRIDES = {
    "device_status": "Device Status",
    "device_name": "Device Name",
    "device_id": "Device ID",
    "firmware_version": "Firmware Version",
    "kernel_version": "Kernel Version",
    "system_load": "System Load",
    "total_memory_bytes": "Total Memory",
    "free_memory_bytes": "Free Memory",
    "running_processes": "Running Processes",
    "system_date_time": "System Date/Time",
    "system_logs": "System Logs",
    "storage_usage": "Storage Usage",
    "filesystem_mounts": "Filesystem Mounts",
    "ethernet_interface": "Ethernet Interface",
    "ethernet_mac_address": "Ethernet MAC Address",
    "lan_subnet_mask": "Subnet Mask",
    "ethernet_link_status": "Ethernet Link Status",
    "ethernet_speed": "Ethernet Speed",
    "ethernet_duplex": "Ethernet Duplex",
    "lan_rx_dropped": "RX Dropped Packets",
    "lan_tx_dropped": "TX Dropped Packets",
    "routing_table": "Routing Table",
    "arp_table": "ARP Table",
    "bridge_information": "Bridge Information",
    "wireless_interface": "Wireless Interface",
    "wireless_mac_address": "Wireless MAC Address",
    "wireless_mode": "Wireless Mode",
    "ssid": "SSID",
    "frequency_mhz": "Frequency",
    "channel": "Channel",
    "channel_width": "Channel Width",
    "tx_power": "TX Power",
    "signal_strength": "Signal Strength",
    "noise_floor": "Noise Floor",
    "wlan_rx_bytes": "Wireless RX Bytes",
    "wlan_tx_bytes": "Wireless TX Bytes",
    "wlan_rx_errors": "Wireless RX Errors",
    "wlan_tx_errors": "Wireless TX Errors",
    "wireless_retries": "Wireless Retries",
    "connected_stations": "Connected Stations",
    "radio_statistics": "Radio Statistics",
    "available_networks": "Available Networks",

    "signal": "Signal Strength",

    "noise": "Noise Floor",

    "ccq": "CCQ",

    "snr": "SNR",

    "wlanTxRate": "TX Data Rate",

    "wlanRxRate": "RX Data Rate",

    "wlanMac": "Wireless MAC Address",

    "wireless_mac": "Wireless MAC Address",

    "lan_ip_address": "LAN IP Address",

    "lan_mac_address": "Ethernet MAC Address",

    "ethernet_mac": "LAN MAC Address",

    "ethernet_interface_state": "Ethernet Link Status",

    "wireless_interface_state": "Wireless Interface State",

    "mac": "Device MAC Address",

    "essid": "SSID",

    "frequency": "Frequency",

    "mode": "Wireless Mode",

    "hostname": "Hostname",

    "side_devicename": "Hostname",

    "devicename": "Hostname",

    "uptime_seconds": "Uptime",

    "ip_address": "Device IP Address",

    "cpu_model": "CPU Model",

    "cpu_usage": "CPU Usage",

    "firmware_upgrade": "Firmware Upgrade",

    "ram_usage_percent": "RAM Usage",

    "ethernet_rx_bytes": "RX Bytes",

    "ethernet_tx_bytes": "TX Bytes",

    "lan_rx_errors": "RX Errors",

    "lan_rx_packets": "RX Packets",

    "lan_tx_errors": "TX Errors",

    "lan_tx_packets": "TX Packets",

    "wireless_rx_bytes": "Wireless RX Bytes",

    "wireless_tx_bytes": "Wireless TX Bytes",

    "wip": "Wireless IP Address",

    "wlan_ip_address": "Wireless IP Address",

    "wmac": "Wireless MAC Address",

    "lmac": "LAN MAC Address",

    "lip": "LAN IP Address",

    "lan_ip_address": "LAN IP Address",

    "lan_mac_address": "Ethernet MAC Address",

    "lan_plugged": "LAN Link Status",

    "plugged": "LAN Link Status",

    "lan_rxbytes": "LAN Received Data",

    "lan_rx_bytes": "LAN Received Data",

    "lan_rxpackets": "LAN Received Packets",

    "lan_rx_packets": "RX Packets",

    "lan_rxerrors": "LAN Receive Errors",

    "lan_rx_errors": "RX Errors",

    "lan_txbytes": "LAN Transmitted Data",

    "lan_tx_bytes": "LAN Transmitted Data",

    "lan_txpackets": "LAN Transmitted Packets",

    "lan_tx_packets": "TX Packets",

    "lan_txerrors": "LAN Transmit Errors",

    "lan_tx_errors": "TX Errors",

    "wlan_rxbytes": "Wireless Received Data",

    "wlan_rxpackets": "Wireless Received Packets",

    "wlan_rxerrors": "Wireless Receive Errors",

    "wlan_txbytes": "Wireless Transmitted Data",

    "wlan_txpackets": "Wireless Transmitted Packets",

    "wlan_txerrors": "Wireless Transmit Errors",

    "channel": "Wireless Channel",

    "security": "Wireless Security",

    "qos": "Wireless QoS",

    "antenna": "Antenna Polarization",

    "ack": "ACK Distance",

    "rstatus": "Wireless Radio Status Code",

    "err_nwids": "Wireless Invalid Network IDs",

    "err_crypts": "Wireless Crypto Errors",

    "err_frags": "Wireless Fragment Errors",

    "err_retries": "Wireless Retries",

    "err_beacons": "Wireless Beacon Errors",

    "err_misc": "Wireless Other Errors",

    "deviceId": "Device ID",

    "firmwareVersion": "Firmware Version",

    "platform": "Platform",

    "deviceIp": "Configured Device IP Address",

    "apmac": "AP MAC", "cfg_crc": "Cfg CRC", "device_model": "Device Model",

    "distance": "Distance", "ack_timeout": "Ack Timeout", "latitude": "Latitude",

    "longitude": "Longitude", "radio_date_time": "Radio Date and Time",

    "ppp_ip": "PPP IP Address", "ppp_rx_errors": "PPP Receive Errors",

    "ppp_rx_bytes": "PPP Received Data", "ppp_rx_packets": "PPP Received Packets",

    "ppp_tx_errors": "PPP Transmit Errors", "ppp_tx_bytes": "PPP Transmitted Data",

    "ppp_tx_packets": "PPP Transmitted Packets",

}





def _friendly_name(key):

    """Return a readable, consistently capitalized name for a sensor key."""

    if key in SENSOR_NAME_OVERRIDES:

        return SENSOR_NAME_OVERRIDES[key]



    # Older AirOS firmware may expose LAN counters using display labels

    # instead of stable machine-readable keys.

    legacy_ethernet_names = {

        "plugged": "LAN Link Status",

        "rx bytes": "LAN Received Data",

        "rx errors": "LAN Receive Errors",

        "rx packets": "LAN Received Packets",

        "tx bytes": "LAN Transmitted Data",

        "tx errors": "LAN Transmit Errors",

        "tx packets": "LAN Transmitted Packets",

    }

    if key.strip().lower() in legacy_ethernet_names:

        return legacy_ethernet_names[key.strip().lower()]



    # Convert camelCase and separators into words before applying protocol terms.

    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key)

    name = re.sub(r"[_-]+", " ", name).strip()

    words = name.split()

    normalized = []

    for word in words:

        lower = word.lower()

        if lower in {"wlan", "wireless", "wifi"}:

            normalized.append("Wireless")

        elif lower in {"lan", "ethernet", "eth"}:

            normalized.append("LAN")

        elif lower in {"mac", "ip", "cpu", "ccq", "snr", "ssid", "tx", "rx", "mhz", "dbm", "id", "url", "ram"}:

            normalized.append(lower.upper())

        else:

            normalized.append(lower.capitalize())

    return " ".join(normalized) or "Unknown"





def _device_kind(key):
    """Return the Home Assistant device that should own this sensor."""
    normalized = key.lower()
    # System/main device
    if key in {"apmac","cfg_crc",
        "device_model","distance","ack_timeout","latitude","longitude","radio_date_time",
        "ppp_ip","ppp_rx_errors","ppp_rx_bytes","ppp_rx_packets","ppp_tx_errors",
        "ppp_tx_bytes","ppp_tx_packets","hostname","uptime_seconds","cpu_model",
        "cpu_usage","ram_usage_percent","firmware_upgrade","deviceId","firmwareVersion",
        "platform","deviceIp","device_status","device_name","device_id","firmware_version",
        "kernel_version","system_load","total_memory_bytes","free_memory_bytes",
        "running_processes","system_date_time","system_logs","storage_usage","filesystem_mounts"}:
        return "main"
    # Wireless
    if normalized.startswith(("wlan", "wireless_")) or key in BASE_SENSORS or key in {
        "essid", "ssid", "frequency", "frequency_mhz", "wireless_mac", "wireless_mac_address",
        "wireless_interface", "wireless_interface_state", "mode", "wireless_mode",
        "wmac", "wip", "channel", "channel_width", "tx_power", "security", "qos", "antenna", "ack", "rstatus",
        "err_nwids", "err_crypts", "err_frags", "err_retries", "err_beacons", "err_misc",
        "signal_strength", "noise_floor", "wlan_rx_bytes", "wlan_tx_bytes", "wlan_rx_errors", "wlan_tx_errors",
        "wireless_retries", "connected_stations", "radio_statistics", "available_networks",
    }:
        return "wireless"
    # Ethernet
    if key in {"ethernet_interface", "ethernet_mac_address", "lan_subnet_mask", "ethernet_link_status",
        "ethernet_speed", "ethernet_duplex", "lan_rx_dropped", "lan_tx_dropped",
        "routing_table", "arp_table", "bridge_information"}:
        return "lan"
    if normalized.startswith(("ethernet_", "lan", "eth")) or normalized in {"ethernet_mac", "lip", "lmac", "mac"}:
        return "lan"
    return "main"

    # Check WLAN first because "lan" is also present inside "wlan".

    if normalized.startswith(("wlan", "wireless_")) or key in BASE_SENSORS or key in {

        "essid", "frequency", "wireless_mac", "wireless_interface_state", "mode",

        "wmac", "wip", "channel", "security", "qos", "antenna", "ack", "rstatus",

        "err_nwids", "err_crypts", "err_frags", "err_retries", "err_beacons", "err_misc",

    }:

        return "wireless"

    # Keep the single canonical uptime sensor on the main device.

    if key == "uptime_seconds":

        return "main"

    # Legacy AirOS keys may call the wired interface "lan" or "eth".

    if normalized.startswith(("ethernet_", "lan", "eth")) or normalized in {"ethernet_mac", "lip", "lmac", "mac"}:

        return "lan"

    return "main"





async def async_setup_entry(hass, entry, async_add_entities):

    coordinator = hass.data[DOMAIN][entry.entry_id]

    data = coordinator.data or {}

    display_name, metadata = _parse_device_name(entry.data["name"])

    # Register the parent device first so child devices can reference its ID.

    device_registry = dr.async_get(hass)

    parent_device = device_registry.async_get_or_create(

        config_entry_id=entry.entry_id,

        identifiers={(DOMAIN, device_identifier(entry.data["host"]))},

        name=display_name,

        manufacturer="Ubiquiti",

        model=(data.get("device_model") or "Original airOS 3.xÔÇô4.x"),

    )



    # Ensure the LAN child exists, then move existing LAN entities

    # back under it. This preserves entity IDs and their history after upgrades.

    host = entry.data["host"]

    lan_device = device_registry.async_get_or_create(

        config_entry_id=entry.entry_id,

        identifiers={(DOMAIN, f"{device_identifier(host)}_lan")},

        name=f"{display_name} Ethernet",

        manufacturer="Ubiquiti",

        model="Original airOS 3.xÔÇô4.x LAN",

        via_device_id=parent_device.id,

    )



    entity_registry = er.async_get(hass)



    # Migrate the previous SSH-only child identifier to the shared LAN identifier

    # used by the HTTP integration. This keeps existing entities and history.

    legacy_lan_device = device_registry.async_get_child_device_by_identifier(

        (DOMAIN, f"{device_identifier(host)}_ethernet"), entry.entry_id

    )

    if legacy_lan_device is not None and legacy_lan_device.id != lan_device.id:

        for registered_entity in list(entity_registry.entities.values()):

            if registered_entity.device_id == legacy_lan_device.id:

                entity_registry.async_update_entity(

                    registered_entity.entity_id, device_id=lan_device.id

                )

        if not any(

            registered_entity.device_id == legacy_lan_device.id

            for registered_entity in entity_registry.entities.values()

        ):

            device_registry.async_remove_device(legacy_lan_device.id)



    # Remove obsolete per-interface devices left by earlier integration builds.

    interface_prefix = f"{display_name} Interface "

    for old_device in device_registry.devices:

        if old_device.id in {lan_device.id, parent_device.id}:

            continue

        if entry.entry_id != old_device.config_entry_id:

            continue

        if not (old_device.name or "").startswith(interface_prefix):

            continue

        for registered_entity in list(entity_registry.entities.values()):

            if registered_entity.device_id == old_device.id:

                entity_registry.async_update_entity(registered_entity.entity_id, device_id=lan_device.id)

        if not any(e.device_id == old_device.id for e in entity_registry.entities.values()):

            device_registry.async_remove_device(old_device.id)

    entity_registry = er.async_get(hass)



    # Keep the device-name sensor on the requested stable entity ID. The unique

    # ID remains unchanged so existing registry metadata and history are retained.

    hostname_entity_id = "sensor.airos_hostname"

    legacy_hostname_ids = {

        f"{host}_side_devicename",

        f"{host}_devicename",

    }

    for entity in list(entity_registry.entities.values()):

        if entity.config_entry_id != entry.entry_id:

            continue

        if entity.unique_id not in legacy_hostname_ids:

            continue

        if entity.entity_id == hostname_entity_id:

            continue

        if entity_registry.async_get(hostname_entity_id) is None:

            entity_registry.async_update_entity(

                entity.entity_id, new_entity_id=hostname_entity_id

            )



    # Correct the registered display name for the canonical device MAC.

    # Older builds may have retained an incorrect "AP MAC" label in the

    # entity registry even though the current sensor description is correct.

    device_mac_unique_id = f"{entry.data['host']}_mac"

    for entity in list(entity_registry.entities.values()):

        if entity.config_entry_id != entry.entry_id:

            continue

        if entity.unique_id == device_mac_unique_id and entity.name != "Device MAC Address":

            entity_registry.async_update_entity(

                entity.entity_id, name="Device MAC Address"

            )



    # Remove obsolete LAN-specific IP/MAC entities belonging to this

    # config entry. Keep the canonical Device IP Address and Device MAC

    # Address sensors, which replace these legacy aliases.

    obsolete_ethernet_entity_ids = {

        "sensor.airos_ethernet_ip_address",

        "sensor.airos_ethernet_mac_address",

    }

    for entity in list(entity_registry.entities.values()):

        if (

            entity.config_entry_id == entry.entry_id

            and entity.entity_id in obsolete_ethernet_entity_ids

        ):

            entity_registry.async_remove(entity.entity_id)



    # Remove registry entries left behind by older releases that exposed raw

    # memory counters as individual sensors. These keys are now attributes on

    # the single RAM Usage sensor, so leaving the old entries creates stale

    # Memory entities in Home Assistant after an upgrade.

    obsolete_memory_keys = {

        "mem_total_bytes",

        "mem_free_bytes",

        "mem_available_bytes",

    }

    host_prefix = f"{host}_"

    for entity in list(entity_registry.entities.values()):

        if entity.config_entry_id != entry.entry_id:

            continue

        if entity.unique_id.startswith(host_prefix):

            old_key = entity.unique_id[len(host_prefix):]

            if old_key in obsolete_memory_keys:

                entity_registry.async_remove(entity.entity_id)



    for entity in entity_registry.entities.values():

        if entity.config_entry_id != entry.entry_id:

            continue

        prefix = f"{host}_"

        if not entity.unique_id.startswith(prefix):

            continue

        key = entity.unique_id[len(prefix):]

        if _device_kind(key) == "lan" and entity.device_id != lan_device.id:

            entity_registry.async_update_entity(

                entity.entity_id, device_id=lan_device.id

            )



    # The first probe may not identify the hardware. Update the main device

    # registry entry on later coordinator refreshes once a specific model appears.

    def _update_registered_device_model():

        """Keep the model label consistent with the HTTP integration."""

        detected_model = (coordinator.data or {}).get("device_model")

        current_device = device_registry.async_get_device_by_identifier(

            (DOMAIN, device_identifier(entry.data["host"])), entry.entry_id

        )

        if current_device and detected_model and current_device.model != detected_model:

            device_registry.async_update_device(current_device.id, model=detected_model)



    entry.async_on_unload(coordinator.async_add_listener(_update_registered_device_model))



    sensors = [

        AiRXS2Sensor(

            coordinator, entry, key, unit, label, display_name=display_name,

            device_kind=_device_kind(key), parent_device_id=parent_device.id,

        )

        for key, (label, unit) in BASE_SENSORS.items()

    ]



    added_keys = set(BASE_SENSORS)

    for key, (label, unit) in OPTIONAL_SENSORS.items():

        # Prefer the MAC reported directly by AirOS over the interface-probe

        # alias when both describe the same wireless interface.

        if key == "wireless_mac" and data.get("wlanMac") not in (None, ""):

            added_keys.add(key)

            continue

        # IP discovery depends on an optional SSH probe. Register the entity

        # even if the first probe fails, so it can become available on later polls.

        if key in {"ip_address", "uptime_seconds", "ethernet_interface_state", "wireless_interface_state", "cpu_usage", "firmware_upgrade", "ram_usage_percent", "lan_rx_errors", "lan_rx_packets", "lan_tx_errors", "lan_tx_packets", "lan_ip_address", "lan_mac_address"} or data.get(key) not in (None, ""):

            sensors.append(

                AiRXS2Sensor(

                    coordinator, entry, key, unit, label,

                    display_name=display_name, device_kind=_device_kind(key),

                    parent_device_id=parent_device.id,

                )

            )

            added_keys.add(key)



    # Keep canonical LAN IP/MAC sensors, suppressing their raw interface aliases.

    added_keys.update({"ethernet_mac", "ethernet_ip_address", "lip", "lmac"})

    # Firmware detail fields are attributes of the single Firmware Upgrade sensor,

    # not separate entities of their own.

    added_keys.update(key for key in data if key.startswith("firmware_upgrade_"))

    # Raw memory counters are attributes of RAM Usage, not separate entities.

    added_keys.update({"mem_total_bytes", "mem_free_bytes", "mem_available_bytes"})



    # Older AirOS output may expose the same RX/TX error counters under

    # LAN-specific aliases as well as the canonical LAN keys. Prefer

    # the LAN Receive/Transmit Errors entities and suppress duplicate aliases.

    duplicate_ethernet_aliases = {

        "ethernet_rx_errors": "lan_rx_errors", "rx errors": "lan_rx_errors",

        "ethernet_tx_errors": "lan_tx_errors", "tx errors": "lan_tx_errors",

        "rx bytes": "ethernet_rx_bytes", "tx bytes": "ethernet_tx_bytes",

        "lan_rxbytes": "ethernet_rx_bytes", "lan_rx_bytes": "ethernet_rx_bytes",

        "lan rx bytes": "ethernet_rx_bytes", "rx bytes": "ethernet_rx_bytes",

        "lan_txbytes": "ethernet_tx_bytes", "lan_tx_bytes": "ethernet_tx_bytes",

        "lan tx bytes": "ethernet_tx_bytes", "tx bytes": "ethernet_tx_bytes",

        "lan_rxerrors": "lan_rx_errors", "lan_rx_errors": "lan_rx_errors",

        "lan rx errors": "lan_rx_errors", "rx errors": "lan_rx_errors",

        "lan_txerrors": "lan_tx_errors", "lan_tx_errors": "lan_tx_errors",

        "lan tx errors": "lan_tx_errors", "tx errors": "lan_tx_errors",

        "lan_rxpackets": "lan_rx_packets", "lan_rx_packets": "lan_rx_packets",

        "lan rx packets": "lan_rx_packets", "rx packets": "lan_rx_packets",

        "lan_txpackets": "lan_tx_packets", "lan_tx_packets": "lan_tx_packets",

        "lan tx packets": "lan_tx_packets", "tx packets": "lan_tx_packets",

    }

    duplicate_requested_aliases = {

        "side_devicename": "hostname", "devicename": "hostname",

        "datetime": "radio_date_time", "date_time": "radio_date_time",

        "radio_datetime": "radio_date_time",

        "ap_mac": "apmac", "ap mac": "apmac", "apmacaddr": "apmac", "wlan_apmac": "apmac",

        "ack timeout": "ack_timeout", "config crc": "cfg_crc", "cfg crc": "cfg_crc",

        "configcrc": "cfg_crc", "config_crc": "cfg_crc", "cfgcrc": "cfg_crc",

        "linkdistance": "distance", "dist": "distance",

        "lat": "latitude", "lon": "longitude", "lng": "longitude",

        "pppip": "ppp_ip", "pppaddress": "ppp_ip",

        "ppp_rxbytes": "ppp_rx_bytes", "ppp_rxpackets": "ppp_rx_packets",

        "ppp_rxerrors": "ppp_rx_errors", "ppp_txbytes": "ppp_tx_bytes",

        "ppp_txpackets": "ppp_tx_packets", "ppp_txerrors": "ppp_tx_errors",

        "wlanrxbytes": "wireless_rx_bytes", "wlantxbytes": "wireless_tx_bytes",

        "wireless_mac": "wlanMac", "ethernet_mac": "mac",

        "lip": "lan_ip_address", "ethernet_ip_address": "lan_ip_address",

        "lmac": "lan_mac_address", "ethernet_mac_address": "lan_mac_address",

    }

    lan_sensor_keys = {"lan_ip_address", "lan_mac_address", "ethernet_interface_state", "ethernet_rx_bytes", "ethernet_tx_bytes", "lan_rx_errors", "lan_rx_packets", "lan_tx_errors", "lan_tx_packets"}

    for key, value in data.items():

        # The LAN device should contain only the nine requested canonical sensors.

        # Suppress interface aliases and any additional raw LAN-only fields.

        if _device_kind(key) == "lan" and key not in lan_sensor_keys:

            added_keys.add(key)

            continue

        canonical_key = duplicate_ethernet_aliases.get(key.strip().lower())

        if canonical_key and data.get(canonical_key) is not None:

            added_keys.add(key)

            continue

        requested_key = duplicate_requested_aliases.get(key.strip().lower())

        if requested_key and data.get(requested_key) not in (None, ""):

            added_keys.add(key)

            continue

        if key not in added_keys and value not in (None, ""):

            sensors.append(

                AiRXS2Sensor(

                    coordinator, entry, key, None, _friendly_name(key),

                    display_name=display_name, device_kind=_device_kind(key),

                    parent_device_id=parent_device.id,

                )

            )



    for key, value in metadata.items():

        # Some legacy AirOS device-name metadata repeats values already

        # exposed by live sensors. Avoid showing the same IP/MAC twice.

        if key == "deviceId" and value == str(data.get("mac", "")):

            continue

        if key == "deviceIp" and value == str(data.get("ip_address", "")):

            continue

        label, unit = DEVICE_METADATA[key]

        sensors.append(

            AiRXS2Sensor(

                coordinator, entry, f"device_metadata_{key}", unit, label,

                display_name=display_name, static_value=value, device_kind="main",

                parent_device_id=parent_device.id,

            )

        )



    # Remove duplicates per device (same key or same name), not across devices.
    seen_keys = set()
    mac_seen = set()
    deduped = []
    for s in sensors:
        kind = getattr(s, "_device_kind", "main")
        key = getattr(s, "key", None) or getattr(s, "_key", None)
        name = (s._attr_name or "").strip().lower()

        key_id = (kind, key) if key else None
        name_id = (kind, name)
        if key_id and key_id in seen_keys:
            continue
        if name_id in seen_keys:
            continue
        if key_id:
            seen_keys.add(key_id)
        seen_keys.add(name_id)

        is_mac = "mac address" in name or name.endswith(" mac") or name == "mac"
        if is_mac:
            if kind in mac_seen:
                continue
            mac_seen.add(kind)

        deduped.append(s)
    sensors = deduped

    sensors.sort(key=lambda s: (s._attr_name or "").lower())
    async_add_entities(sensors)





class AiRXS2Sensor(SensorEntity):

    _attr_has_entity_name = True



    def __init__(

        self, coordinator, entry, key, unit, label=None, display_name=None,

        static_value=None, device_kind="main", unique_id_suffix=None,

        parent_device_id=None,

    ):

        self.coordinator = coordinator

        self.key = key

        self._entry = entry

        self._display_name = display_name or entry.data["name"]

        self._static_value = static_value

        self._device_kind = device_kind

        self._parent_device_id = parent_device_id

        if device_kind == "lan":

            self._device_name = f"{self._display_name} Ethernet"

        elif device_kind == "wireless":

            self._device_name = f"{self._display_name} Wireless"

        else:

            self._device_name = self._display_name

        self._attr_icon = {

            "signal": "mdi:signal",

            "noise": "mdi:waveform",

            "ccq": "mdi:chart-line",

            "snr": "mdi:signal",

            "wlanTxRate": "mdi:upload",

            "wlanRxRate": "mdi:download",

            "frequency": "mdi:sine-wave",

            "essid": "mdi:wifi",

            "wlanMac": "mdi:network-outline",

            "mac": "mdi:lan",

            "hostname": "mdi:form-textbox",

            "ip_address": "mdi:ip-network",

            "uptime_seconds": "mdi:timer-outline",

            "cpu_usage": "mdi:cpu-64-bit",

            "ram_usage_percent": "mdi:memory",

            "firmware_upgrade": "mdi:chip",

            "ethernet_rx_bytes": "mdi:download-network",

            "ethernet_tx_bytes": "mdi:upload-network",

            "wireless_rx_bytes": "mdi:download-network",

            "wireless_tx_bytes": "mdi:upload-network",

            "lan_rxbytes": "mdi:download-network",

            "lan_txbytes": "mdi:upload-network",

            "wlan_rxbytes": "mdi:download-network",

            "wlan_txbytes": "mdi:upload-network",

            "ppp_rxbytes": "mdi:download-network",

            "ppp_txbytes": "mdi:upload-network",

            "device_model": "mdi:router-wireless",

            "deviceId": "mdi:identifier",

            "firmwareVersion": "mdi:package-variant",

            "distance": "mdi:map-marker-distance",

            "latitude": "mdi:latitude",

            "longitude": "mdi:longitude",

            "radio_date_time": "mdi:clock-outline",

        }.get(key)

        self._attr_name = label or _friendly_name(key)

        self._attr_unique_id = f"{entry.data['host']}_{key}" + (

            f"_{unique_id_suffix}" if unique_id_suffix else ""

        )

        if unit:

            self._attr_native_unit_of_measurement = unit



        # Tell Home Assistant how to interpret readings and long-term statistics.

        if key in {"signal", "noise"}:

            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH

        elif key == "frequency":

            self._attr_device_class = SensorDeviceClass.FREQUENCY

        elif key == "uptime_seconds":

            self._attr_device_class = SensorDeviceClass.DURATION

        elif key in {"ethernet_rx_bytes", "ethernet_tx_bytes",

                     "wireless_rx_bytes", "wireless_tx_bytes"}:

            self._attr_device_class = SensorDeviceClass.DATA_SIZE



        if key in {"ethernet_rx_bytes", "ethernet_tx_bytes",

                   "wireless_rx_bytes", "wireless_tx_bytes"}:

            self._attr_state_class = SensorStateClass.TOTAL_INCREASING

        elif key in {"signal", "noise", "ccq", "snr", "wlanTxRate", "wlanRxRate",

                     "frequency", "cpu_usage",

                     "ram_usage_percent"}:

            self._attr_state_class = SensorStateClass.MEASUREMENT




        diagnostic_keys = {
            "device_id", "deviceId", "firmwareVersion", "firmware_version", "firmware_upgrade",
            "kernel_version", "uptime_seconds", "cpu_usage", "system_load",
            "total_memory_bytes", "free_memory_bytes", "ram_usage_percent",
            "running_processes", "system_date_time", "system_logs", "storage_usage", "filesystem_mounts",
            "ip_address", "deviceIp", "mac", "hostname", "device_name", "device_model", "platform",
            "ethernet_interface", "ethernet_mac_address", "lan_ip_address", "lan_subnet_mask",
            "ethernet_link_status", "ethernet_speed", "ethernet_duplex",
            "lan_rx_errors", "lan_tx_errors", "lan_rx_dropped", "lan_tx_dropped",
            "routing_table", "arp_table", "bridge_information",
            "wireless_interface", "wireless_mac_address", "wlanMac", "wireless_mac",
            "wireless_interface_state", "wireless_mode", "mode", "ssid", "essid",
            "channel", "channel_width", "tx_power", "frequency", "frequency_mhz",
            "apmac", "cfg_crc", "distance", "ack_timeout", "latitude", "longitude",
            "radio_date_time", "radio_statistics", "connected_stations", "available_networks",
        }
        if key in diagnostic_keys or key.startswith("firmware_upgrade_") or key.startswith("mem_"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property

    def device_info(self):

        host = self._entry.data["host"]

        info = {

            "identifiers": {(DOMAIN, device_identifier(host) if self._device_kind == "main" else f"{device_identifier(host)}_{self._device_kind}")},

            "name": self._device_name,

            "manufacturer": "Ubiquiti",

            "model": (

                (self.coordinator.data or {}).get("device_model") or "Original airOS 3.xÔÇô4.x"

            ) if self._device_kind == "main" else (

                ((self.coordinator.data or {}).get("device_model") or "Original airOS 3.xÔÇô4.x")

                + (" Ethernet" if self._device_kind == "lan" else " Wireless")

            ),

        }

        if self._device_kind != "main":

            info["via_device_id"] = self._parent_device_id

        return DeviceInfo(**info)



    @property

    def native_value(self):

        if self._static_value is not None:

            return self._static_value

        return (self.coordinator.data or {}).get(self.key)



    @property

    def extra_state_attributes(self):

        data = self.coordinator.data or {}

        if self.key == "ram_usage_percent":

            return {

                key: data[key]

                for key in ("mem_total_bytes", "mem_free_bytes", "mem_available_bytes")

                if data.get(key) is not None

            }

        if self.key != "firmware_upgrade":

            return None

        return {

            key.removeprefix("firmware_upgrade_"): data[key]

            for key in (

                "firmware_upgrade_installed_version",

                "firmware_upgrade_latest_version",

                "firmware_upgrade_reason",

                "firmware_upgrade_source",

            )

            if data.get(key) is not None

        }

