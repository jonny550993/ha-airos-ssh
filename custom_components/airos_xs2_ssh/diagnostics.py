"""Diagnostics support for the AirOS SSH integration."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {
    "host",
    "username",
    "password",
    "device_name",
    "device_id",
    "lan_ip",
    "eth_mac",
    "wlan_mac",
    "ssid",
    "system_logs_raw",
    "running_processes_raw",
    "routing_table_raw",
    "arp_table_raw",
    "bridge_info_raw",
    "connected_stations_raw",
    "available_networks_raw",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "config_entry": async_redact_data(entry.data, TO_REDACT),
        "coordinator_data": async_redact_data(coordinator.data or {}, TO_REDACT),
    }
