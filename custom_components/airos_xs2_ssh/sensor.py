from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfDataRate,
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, device_identifier


@dataclass(frozen=True, kw_only=True)
class AirOSSensorDescription(SensorEntityDescription):
    raw_key: str | None = None


SENSORS: tuple[AirOSSensorDescription, ...] = (
    # 1. System
    AirOSSensorDescription(key="device_status", name="Device Status", icon="mdi:router-network", raw_key="device_status_raw", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="device_name", name="Device Name", icon="mdi:form-textbox"),
    AirOSSensorDescription(key="device_model", name="Device Model", icon="mdi:router-wireless"),
    AirOSSensorDescription(key="device_id", name="Device ID", icon="mdi:identifier", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="firmware_version", name="Firmware Version", icon="mdi:package-variant", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="kernel_version", name="Kernel Version", icon="mdi:chip", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="uptime", name="Uptime", icon="mdi:timer-outline"),
    AirOSSensorDescription(key="cpu_usage", name="CPU Usage", icon="mdi:cpu-64-bit", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="system_load", name="System Load", icon="mdi:gauge"),
    AirOSSensorDescription(key="memory_total", name="Total Memory", icon="mdi:memory", native_unit_of_measurement="kB", state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="memory_free", name="Free Memory", icon="mdi:memory", native_unit_of_measurement="kB", state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="running_processes", name="Running Processes", icon="mdi:format-list-numbered", state_class=SensorStateClass.MEASUREMENT, raw_key="running_processes_raw", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="system_datetime", name="System Date/Time", icon="mdi:clock-outline"),
    AirOSSensorDescription(key="system_logs", name="System Logs", icon="mdi:text-box-outline", raw_key="system_logs_raw", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="storage_usage", name="Storage Usage", icon="mdi:harddisk", raw_key="storage_usage_raw", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="filesystem_mounts", name="Filesystem Mounts", icon="mdi:folder-network-outline", state_class=SensorStateClass.MEASUREMENT, raw_key="filesystem_mounts_raw", entity_category=EntityCategory.DIAGNOSTIC),
    # 2. Ethernet
    AirOSSensorDescription(key="eth_interface", name="Ethernet Interface", icon="mdi:ethernet", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="eth_mac", name="Ethernet MAC Address", icon="mdi:ethernet", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="lan_ip", name="LAN IP Address", icon="mdi:ip-network"),
    AirOSSensorDescription(key="lan_subnet", name="Subnet Mask", icon="mdi:ip-network-outline", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="eth_link_status", name="Ethernet Link Status", icon="mdi:ethernet-cable"),
    AirOSSensorDescription(key="eth_speed", name="Ethernet Speed", icon="mdi:speedometer", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="eth_duplex", name="Ethernet Duplex", icon="mdi:swap-horizontal", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="eth_rx_bytes", name="Ethernet RX Bytes", icon="mdi:download-network", native_unit_of_measurement=UnitOfInformation.BYTES, device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.TOTAL_INCREASING),
    AirOSSensorDescription(key="eth_tx_bytes", name="Ethernet TX Bytes", icon="mdi:upload-network", native_unit_of_measurement=UnitOfInformation.BYTES, device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.TOTAL_INCREASING),
    AirOSSensorDescription(key="eth_rx_packets", name="Ethernet RX Packets", icon="mdi:download-network-outline", state_class=SensorStateClass.TOTAL_INCREASING),
    AirOSSensorDescription(key="eth_tx_packets", name="Ethernet TX Packets", icon="mdi:upload-network-outline", state_class=SensorStateClass.TOTAL_INCREASING),
    AirOSSensorDescription(key="eth_rx_errors", name="Ethernet RX Errors", icon="mdi:alert-circle-outline", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="eth_tx_errors", name="Ethernet TX Errors", icon="mdi:alert-circle-outline", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="eth_rx_dropped", name="Ethernet RX Dropped Packets", icon="mdi:tray-remove", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="eth_tx_dropped", name="Ethernet TX Dropped Packets", icon="mdi:tray-remove", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="routing_table", name="Routing Table", icon="mdi:routes", state_class=SensorStateClass.MEASUREMENT, raw_key="routing_table_raw", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="arp_table", name="ARP Table", icon="mdi:table-network", state_class=SensorStateClass.MEASUREMENT, raw_key="arp_table_raw", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="bridge_info", name="Bridge Information", icon="mdi:bridge", state_class=SensorStateClass.MEASUREMENT, raw_key="bridge_info_raw", entity_category=EntityCategory.DIAGNOSTIC),
    # 3. Wireless
    AirOSSensorDescription(key="wlan_interface", name="Wireless Interface", icon="mdi:wifi", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="wlan_mac", name="Wireless MAC Address", icon="mdi:wifi-cog", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="wireless_mode", name="Wireless Mode", icon="mdi:access-point"),
    AirOSSensorDescription(key="ssid", name="SSID", icon="mdi:wifi"),
    AirOSSensorDescription(key="frequency", name="Frequency", icon="mdi:sine-wave", native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="channel", name="Channel", icon="mdi:radio-tower", state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="channel_width", name="Channel Width", icon="mdi:arrow-expand-horizontal", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="tx_power", name="TX Power", icon="mdi:transmission-tower", native_unit_of_measurement="dBm", state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="signal_strength", name="Signal Strength", icon="mdi:signal", native_unit_of_measurement="dBm", device_class=SensorDeviceClass.SIGNAL_STRENGTH, state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="noise_floor", name="Noise Floor", icon="mdi:waveform", native_unit_of_measurement="dBm", device_class=SensorDeviceClass.SIGNAL_STRENGTH, state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="snr", name="SNR", icon="mdi:signal-distance-variant", native_unit_of_measurement="dB", state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="ccq", name="CCQ", icon="mdi:chart-line", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="tx_data_rate", name="TX Data Rate", icon="mdi:upload", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="rx_data_rate", name="RX Data Rate", icon="mdi:download", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT),
    AirOSSensorDescription(key="wlan_rx_bytes", name="Wireless RX Bytes", icon="mdi:download-network", native_unit_of_measurement=UnitOfInformation.BYTES, device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.TOTAL_INCREASING),
    AirOSSensorDescription(key="wlan_tx_bytes", name="Wireless TX Bytes", icon="mdi:upload-network", native_unit_of_measurement=UnitOfInformation.BYTES, device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.TOTAL_INCREASING),
    AirOSSensorDescription(key="wlan_rx_errors", name="Wireless RX Errors", icon="mdi:alert-circle-outline", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="wlan_tx_errors", name="Wireless TX Errors", icon="mdi:alert-circle-outline", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="wireless_retries", name="Wireless Retries", icon="mdi:refresh", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="connected_stations", name="Connected Stations", icon="mdi:devices", state_class=SensorStateClass.MEASUREMENT, raw_key="connected_stations_raw"),
    AirOSSensorDescription(key="radio_statistics", name="Radio Statistics", icon="mdi:chart-box-outline", raw_key="radio_statistics_raw", entity_category=EntityCategory.DIAGNOSTIC),
    AirOSSensorDescription(key="available_networks", name="Available Networks", icon="mdi:wifi-search", state_class=SensorStateClass.MEASUREMENT, raw_key="available_networks_raw", entity_category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AirOSSensor(coordinator, entry, description) for description in SENSORS
    )


class AirOSSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description: AirOSSensorDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{device_identifier(entry.data['host'])}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_identifier(entry.data["host"]))},
            name=(entry.data.get("name") or "NanoStation5 Legacy").split(",")[0].strip(),
            manufacturer="Ubiquiti",
            model=(coordinator.data or {}).get("device_model") or "NanoStation5 Legacy",
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self):
        raw_key = self.entity_description.raw_key
        if not raw_key:
            return None
        data = self.coordinator.data or {}
        raw = data.get(raw_key)
        if raw is None:
            return None
        # Keep attribute size bounded for HA state machine
        text = str(raw)
        if len(text) > 16000:
            text = text[:16000] + "\n... (truncated)"
        return {"raw": text}
