"""Coordinator for Nescafe BLE integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, override

from bleak.backends.device import BLEDevice
from bleak_retry_connector import close_stale_connections_by_address
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothReachabilityIntent
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .nescafe_client import NescafeBleClient, NescafeData

_LOGGER = logging.getLogger(__name__)

type NescafeConfigEntry = ConfigEntry[NescafeDataUpdateCoordinator]


class NescafeDataUpdateCoordinator(DataUpdateCoordinator[NescafeData]):
    config_entry: NescafeConfigEntry

    def __init__(self, hass: HomeAssistant, entry: NescafeConfigEntry) -> None:
        self._device: BLEDevice | None = None

        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    def update_scan_interval(self, seconds: int) -> None:
        self.update_interval = timedelta(seconds=seconds)

    _busy: bool = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    def set_busy(self, value: bool) -> None:
        self._busy = value

    @override
    async def _async_setup(self) -> None:
        address = self.config_entry.unique_id
        assert address is not None

        await close_stale_connections_by_address(address)

        ble_device = bluetooth.async_ble_device_from_address(self.hass, address)
        if not ble_device:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
                translation_placeholders={
                    "address": address,
                    "reason": bluetooth.async_address_reachability_diagnostics(
                        self.hass,
                        address.upper(),
                        BluetoothReachabilityIntent.CONNECTION,
                    ),
                },
            )
        self._device = ble_device

    @override
    async def _async_update_data(self) -> NescafeData:
        assert self._device is not None

        if self._busy:
            _LOGGER.debug("Skipping poll — button operation in progress")
            return self.data

        await close_stale_connections_by_address(self._device.address)
        client = NescafeBleClient(self._device)
        try:
            await client.connect(timeout=15.0)
            return await client.fetch_all()
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch Nescafe data: {err}") from err
        finally:
            await client.disconnect()
