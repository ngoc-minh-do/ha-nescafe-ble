"""Nescafe Barista BLE integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .const import CONF_SCAN_INTERVAL
from .coordinator import NescafeDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import NescafeConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: NescafeConfigEntry) -> bool:
    coordinator = NescafeDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NescafeConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_options(hass: HomeAssistant, entry: NescafeConfigEntry) -> None:
    coordinator = entry.runtime_data
    if CONF_SCAN_INTERVAL in entry.options:
        coordinator.update_scan_interval(entry.options[CONF_SCAN_INTERVAL])
