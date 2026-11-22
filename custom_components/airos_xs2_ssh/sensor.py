"""Sensor platform for Ubiquiti AirOS (SSH)."""

from __future__ import annotations

import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, device_identifier

# Sensors grouped by the device/section they belong to.
# (key, label, unit, device_class, state_class, icon)
SYSTEM_SENSORS = [
    ("device_status", "Device Status", None, None, None, "mdi:lan-connect"),
    ("device_name", "Device Name", None, None, None, "mdi:form-textbox"),
    ("device_model", "Device Model", None, None, None, "mdi:router-wireless"),
    ("device_id", "Device ID", None, None, None, "mdi:identifier"),
    ("firmware_version", "Firmware Version", None, None, None, "mdi:package-variant"),
    ("kernel_version", "Kernel Version", None, None, None, "mdi:chip"),
    ("uptime_seconds", "Uptime", "s", SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT, "mdi:timer-outline"),
    ("cpu_usage", "CPU Usage", "%", None, SensorStateClass.MEASUREMENT, "mdi:cpu-64-bit"),
    ("system_load", "System Load", None, None, None, "mdi:gauge"),
    ("total_memory_bytes", "Total Memory", "B", SensorDeviceClass.DATA_SIZE, SensorStateClass.MEASUREMENT, "mdi:memory"),
    ("free_memory_bytes", "Free Memory", "B", SensorDeviceClass.DATA_SIZE, SensorStateClass.MEASUREMENT, "mdi:memory"),
    ("running_processes", "Running Processes", None, None, SensorStateClass.MEASUREMENT, "mdi:format-list-numbered"),
    ("system_date_time", "System Date/Time", None, None, None, "mdi:clock-outline"),
    ("system_logs", "System Logs", None, None, None, "mdi:text-box-outline"),
    ("storage_usage", "Storage Usage", None, None, None, "mdi:harddisk"),
    ("filesystem_mounts", "Filesystem Mounts", None, None, None, "mdi:folder-outline"),
    ("firmware_upgrade", "Firmware Upgrade", None, None, None, "mdi:update"),
]

ETHERNET_SENSORS = [
    ("ethernet_interface", "Ethernet Interface", None, None, None, "mdi:ethernet"),
    ("ethernet_mac_address", "Ethernet MAC Address", None, None, None, "mdi:network-outline"),
    ("lan_ip_address", "LAN IP Address", None, None, None, "mdi:ip-network"),
    ("lan_subnet_mask", "Subnet Mask", None, None, None, "mdi:ip-network-outline"),
    ("ethernet_link_status", "Ethernet Link Status", None, None, None, "mdi:ethernet-cable"),
    ("ethernet_speed", "Ethernet Speed", None, None, None, "mdi:speedometer"),
    ("ethernet_duplex", "Ethernet Duplex", None, None, None, "mdi:swap-horizontal"),
    ("ethernet_rx_bytes", "RX Bytes", "B", SensorDeviceClass.DATA_SIZE, SensorStateClass.TOTAL_INCREASING, "mdi:download-network"),
    ("ethernet_tx_bytes", "TX Bytes", "B", SensorDeviceClass.DATA_SIZE, SensorStateClass.TOTAL_INCREASING, "mdi:upload-network"),
    ("lan_rx_packets", "RX Packets", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:download-network"),
    ("lan_tx_packets", "TX Packets", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:upload-network"),
    ("lan_rx_errors", "RX Errors", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:alert-circle-outline"),
    ("lan_tx_errors", "TX Errors", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:alert-circle-outline"),
    ("lan_rx_dropped", "RX Dropped Packets", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:tray-arrow-down"),
    ("lan_tx_dropped", "TX Dropped Packets", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:tray-arrow-up"),
    ("routing_table", "Routing Table", None, None, None, "mdi:routes"),
    ("arp_table", "ARP Table", None, None, None, "mdi:table"),
    ("bridge_information", "Bridge Information", None, None, None, "mdi:bridge"),
]

WIRELESS_SENSORS = [
    ("wireless_interface", "Wireless Interface", None, None, None, "mdi:wifi"),
    ("wireless_mac_address", "Wireless MAC Address", None, None, None, "mdi:network-outline"),
    ("wireless_mode", "Wireless Mode", None, None, None, "mdi:wifi-cog"),
    ("ssid", "SSID", None, None, None, "mdi:wifi"),
    ("frequency_mhz", "Frequency", "MHz", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, "mdi:sine-wave"),
    ("channel", "Channel", None, None, None, "mdi:radio-tower"),
    ("channel_width", "Channel Width", None, None, None, "mdi:arrow-expand-horizontal"),
    ("tx_power", "TX Power", None, None, None, "mdi:transmission-tower"),
    ("signal_strength", "Signal Strength", "dBm", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, "mdi:signal"),
    ("noise_floor", "Noise Floor", "dBm", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, "mdi:waveform"),
    ("snr", "SNR", "dB", None, SensorStateClass.MEASUREMENT, "mdi:signal"),
    ("ccq", "CCQ", "%", None, SensorStateClass.MEASUREMENT, "mdi:chart-line"),
    ("wlanTxRate", "TX Data Rate", "Mbit/s", SensorDeviceClass.DATA_RATE, SensorStateClass.MEASUREMENT, "mdi:upload"),
    ("wlanRxRate", "RX Data Rate", "Mbit/s", SensorDeviceClass.DATA_RATE, SensorStateClass.MEASUREMENT, "mdi:download"),
    ("wlan_rx_bytes", "Wireless RX Bytes", "B", SensorDeviceClass.DATA_SIZE, SensorStateClass.TOTAL_INCREASING, "mdi:download-network"),
    ("wlan_tx_bytes", "Wireless TX Bytes", "B", SensorDeviceClass.DATA_SIZE, SensorStateClass.TOTAL_INCREASING, "mdi:upload-network"),
    ("wlan_rx_errors", "Wireless RX Errors", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:alert-circle-outline"),
    ("wlan_tx_errors", "Wireless TX Errors", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:alert-circle-outline"),
    ("wireless_retries", "Wireless Retries", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:refresh"),
    ("connected_stations", "Connected Stations", None, None, None, "mdi:access-point-network"),
    ("radio_statistics", "Radio Statistics", None, None, None, "mdi:chart-box-outline"),
    ("available_networks", "Available Networks", None, None, None, "mdi:wifi-search"),
]

# Backward-compatible aliases: old key -> new key (for data lookup).
KEY_ALIASES = {
    "signal": "signal_strength",
    "noise": "noise_floor",
    "frequency": "frequency_mhz",
    "wireless_rx_bytes": "wlan_rx_bytes",
    "wireless_tx_bytes": "wlan_tx_bytes",
    "wireless_rx_errors": "wlan_rx_errors",
    "wireless_tx_errors": "wlan_tx_errors",
    "hostname": "device_name",
    "firmwareVersion": "firmware_version",
}

# For entity registry migration: old unique_id suffixes that map to a new key.
LEGACY_KEY_MIGRATIONS = {
    "hostname": "device_name",
    "side_devicename": "device_name",
    "devicename": "device_name",
    "signal": "signal_strength",
    "noise": "noise_floor",
    "frequency": "frequency_mhz",
    "wireless_rx_bytes": "wlan_rx_bytes",
    "wireless_tx_bytes": "wlan_tx_bytes",
    "wireless_mac": "wireless_mac_address",
    "wlanMac": "wireless_mac_address",
    "mac": "ethernet_mac_address",
    "lan_mac_address": "ethernet_mac_address",
    "ethernet_mac": "ethernet_mac_address",
    "firmwareVersion": "firmware_version",
    "deviceId": "device_id",
}


def _parse_device_name(raw_name: str) -> tuple[str, dict]:
    """Split comma-separated AirOS metadata out of the device display name."""
    parts = [part.strip() for part in str(raw_name).split(",")]
    metadata = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        if k.strip() and v.strip():
            metadata[k.strip()] = v.strip()
    return (parts[0] or "AirOS Device"), metadata


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    display_name, _ = _parse_device_name(entry.data["name"])
    host = entry.data["host"]
    dev_id = device_identifier(host)

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # Main/System device
    system_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, dev_id)},
        name=display_name,
        manufacturer="Ubiquiti",
        model=data.get("device_model") or "Original airOS 3.x–4.x",
    )

    # Ethernet child device (keep _lan identifier for backward compatibility)
    ethernet_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{dev_id}_lan")},
        name=f"{display_name} Ethernet",
        manufacturer="Ubiquiti",
        model=(data.get("device_model") or "Original airOS 3.x–4.x") + " Ethernet",
        via_device_id=system_device.id,
    )

    # Wireless child device
    wireless_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{dev_id}_wireless")},
        name=f"{display_name} Wireless",
        manufacturer="Ubiquiti",
        model=(data.get("device_model") or "Original airOS 3.x–4.x") + " Wireless",
        via_device_id=system_device.id,
    )

    # Migrate legacy lan/ethernet child identifiers
    for legacy_suffix in ("_ethernet",):
        legacy = device_registry.async_get_device({(DOMAIN, f"{dev_id}{legacy_suffix}")})
        if legacy and legacy.id != ethernet_device.id:
            for ent in list(entity_registry.entities.values()):
                if ent.device_id == legacy.id:
                    entity_registry.async_update_entity(ent.entity_id, device_id=ethernet_device.id)
            if not any(e.device_id == legacy.id for e in entity_registry.entities.values()):
                device_registry.async_remove_device(legacy.id)

    # Migrate old entity unique_ids to new keys where appropriate
    for ent in list(entity_registry.entities.values()):
        if ent.config_entry_id != entry.entry_id or ent.domain != "sensor":
            continue
        prefix = f"{host}_"
        if not ent.unique_id.startswith(prefix):
            continue
        old_key = ent.unique_id[len(prefix):]
        new_key = LEGACY_KEY_MIGRATIONS.get(old_key)
        if not new_key or new_key == old_key:
            continue
        new_unique_id = f"{host}_{new_key}"
        if entity_registry.async_get_entity_id("sensor", DOMAIN, new_unique_id):
            continue
        entity_registry.async_update_entity(ent.entity_id, new_unique_id=new_unique_id)

    # Move entities to correct devices based on their key
    ethernet_keys = {s[0] for s in ETHERNET_SENSORS}
    wireless_keys = {s[0] for s in WIRELESS_SENSORS}
    system_keys = {s[0] for s in SYSTEM_SENSORS}

    for ent in list(entity_registry.entities.values()):
        if ent.config_entry_id != entry.entry_id or ent.domain != "sensor":
            continue
        prefix = f"{host}_"
        if not ent.unique_id.startswith(prefix):
            continue
        key = ent.unique_id[len(prefix):]
        target = None
        if key in ethernet_keys:
            target = ethernet_device.id
        elif key in wireless_keys:
            target = wireless_device.id
        elif key in system_keys:
            target = system_device.id
        if target and ent.device_id != target:
            entity_registry.async_update_entity(ent.entity_id, device_id=target)

    def _update_device_model():
        detected = (coordinator.data or {}).get("device_model")
        if not detected:
            return
        for dev, suffix in ((system_device, ""), (ethernet_device, " Ethernet"), (wireless_device, " Wireless")):
            current = device_registry.async_get(dev.id)
            model = detected + suffix
            if current and current.model != model:
                device_registry.async_update_device(current.id, model=model)

    entry.async_on_unload(coordinator.async_add_listener(_update_device_model))

    entities: list[AiRXS2Sensor] = []
    for key, label, unit, dev_cls, state_cls, icon in SYSTEM_SENSORS:
        entities.append(AiRXS2Sensor(coordinator, entry, key, label, unit, dev_cls, state_cls, icon, "system", system_device.id))
    for key, label, unit, dev_cls, state_cls, icon in ETHERNET_SENSORS:
        entities.append(AiRXS2Sensor(coordinator, entry, key, label, unit, dev_cls, state_cls, icon, "ethernet", ethernet_device.id))
    for key, label, unit, dev_cls, state_cls, icon in WIRELESS_SENSORS:
        entities.append(AiRXS2Sensor(coordinator, entry, key, label, unit, dev_cls, state_cls, icon, "wireless", wireless_device.id))

    async_add_entities(entities)


class AiRXS2Sensor(SensorEntity):
    """Representation of an AirOS sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key, label, unit, dev_cls, state_cls, icon, device_kind, device_id):
        self.coordinator = coordinator
        self._entry = entry
        self._key = key
        self._device_kind = device_kind
        self._ha_device_id = device_id
        self._attr_unique_id = f"{entry.data['host']}_{key}"
        self._attr_name = label
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = dev_cls
        self._attr_state_class = state_cls
        self._attr_icon = icon

    @property
    def device_info(self) -> DeviceInfo:
        host = self._entry.data["host"]
        dev_id = device_identifier(host)
        data = self.coordinator.data or {}
        base_model = data.get("device_model") or "Original airOS 3.x–4.x"
        if self._device_kind == "system":
            return DeviceInfo(
                identifiers={(DOMAIN, dev_id)},
                name=_parse_device_name(self._entry.data["name"])[0],
                manufacturer="Ubiquiti",
                model=base_model,
            )
        suffix = "Ethernet" if self._device_kind == "ethernet" else "Wireless"
        ident_suffix = "_lan" if self._device_kind == "ethernet" else "_wireless"
        return DeviceInfo(
            identifiers={(DOMAIN, f"{dev_id}{ident_suffix}")},
            name=f"{_parse_device_name(self._entry.data['name'])[0]} {suffix}",
            manufacturer="Ubiquiti",
            model=f"{base_model} {suffix}",
            via_device=(DOMAIN, dev_id),
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        # Direct key
        if self._key in data and data[self._key] not in (None, ""):
            return data[self._key]
        # Aliases - look up old keys that map to this key
        for old, new in KEY_ALIASES.items():
            if new == self._key and data.get(old) not in (None, ""):
                return data[old]
        # Common fallbacks
        fallbacks = {
            "device_name": ["hostname", "side_devicename", "devicename"],
            "device_id": ["deviceId", "mac", "wlanMac"],
            "firmware_version": ["firmwareVersion", "firmware_upgrade_installed_version"],
            "signal_strength": ["signal"],
            "noise_floor": ["noise"],
            "frequency_mhz": ["frequency"],
            "wireless_mac_address": ["wlanMac", "wireless_mac"],
            "ethernet_mac_address": ["lan_mac_address", "ethernet_mac", "mac"],
            "wlan_rx_bytes": ["wireless_rx_bytes"],
            "wlan_tx_bytes": ["wireless_tx_bytes"],
            "wlan_rx_errors": ["wireless_rx_errors"],
            "wlan_tx_errors": ["wireless_tx_errors"],
            "ssid": ["essid"],
        }
        for fk in fallbacks.get(self._key, []):
            if data.get(fk) not in (None, ""):
                return data[fk]
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        if self._key == "system_logs":
            full = data.get("_system_logs_full")
            if full:
                return {"full_log_tail": full}
        if self._key == "connected_stations" and data.get("connected_station_count") is not None:
            return {"count": data["connected_station_count"]}
        if self._key == "available_networks" and data.get("available_networks_count") is not None:
            return {"count": data["available_networks_count"]}
        if self._key == "firmware_upgrade":
            attrs = {}
            for src, dst in (
                ("firmware_upgrade_installed_version", "installed_version"),
                ("firmware_upgrade_latest_version", "latest_version"),
                ("firmware_upgrade_reason", "reason"),
                ("firmware_upgrade_source", "source"),
            ):
                if data.get(src) is not None:
                    attrs[dst] = data[src]
            return attrs or None
        return None

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        # System status should be available when coordinator succeeded.
        if self._key == "device_status":
            return True
        return self.native_value is not None
