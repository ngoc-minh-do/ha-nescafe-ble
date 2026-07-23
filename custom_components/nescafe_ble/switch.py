"""Switch platform for Nescafe BLE."""

from __future__ import annotations

import logging
from typing import override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import MANUFACTURER
from .coordinator import NescafeConfigEntry, NescafeDataUpdateCoordinator
from .nescafe_client import NescafeBleClient

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NescafeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    address = entry.unique_id or ""

    async_add_entities(
        [
            NescafePowerSwitch(coordinator, address),
        ]
    )


class NescafePowerSwitch(CoordinatorEntity[NescafeDataUpdateCoordinator], SwitchEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NescafeDataUpdateCoordinator,
        address: str,
    ) -> None:
        super().__init__(coordinator)
        self._address = address
        self._attr_unique_id = f"{address}_power"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            name="Nescafe Barista",
            manufacturer=MANUFACTURER,
            model="Gold Blend Barista Slim (SPM9640)",
        )
        self.entity_description = SwitchEntityDescription(
            key="power",
            translation_key="power",
            name="Power",
            entity_category=EntityCategory.CONFIG,
        )

    @property
    @override
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None or data.status is None:
            return None
        return data.status.state_name in ("ready", "preheat", "extract")

    async def async_turn_on(self, **kwargs) -> None:
        await self._send_power_toggle()

    async def async_turn_off(self, **kwargs) -> None:
        await self._send_power_toggle()

    async def _send_power_toggle(self) -> None:
        from homeassistant.components import bluetooth
        from bleak_retry_connector import close_stale_connections_by_address

        await close_stale_connections_by_address(self._address)
        ble_device = bluetooth.async_ble_device_from_address(
            self.coordinator.hass, self._address
        )
        if ble_device is None:
            _LOGGER.error("BLE device %s not found", self._address)
            return

        client = NescafeBleClient(ble_device)
        try:
            await client.connect(timeout=15.0)
            await client.power_on_off()
        except Exception:
            _LOGGER.exception("Failed to toggle power")
        finally:
            await client.disconnect()
