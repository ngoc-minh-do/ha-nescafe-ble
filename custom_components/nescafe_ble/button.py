"""Button platform for Nescafe BLE."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ACTION_BUTTONS, MANUFACTURER, RECIPE_BUTTONS
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

    entities: list[NescafeButton] = []

    for recipe_key, recipe_name in RECIPE_BUTTONS.items():
        entities.append(
            NescafeButton(
                coordinator,
                address,
                ButtonEntityDescription(
                    key=f"brew_{recipe_key}",
                    translation_key=f"brew_{recipe_key}",
                    name=recipe_name,
                ),
                recipe_key,
            )
        )

    for action_key, action_name in ACTION_BUTTONS.items():
        entities.append(
            NescafeButton(
                coordinator,
                address,
                ButtonEntityDescription(
                    key=f"action_{action_key}",
                    translation_key=f"action_{action_key}",
                    name=action_name,
                    entity_category=EntityCategory.CONFIG,
                ),
                action_key,
            )
        )

    async_add_entities(entities)


class NescafeButton(CoordinatorEntity[NescafeDataUpdateCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NescafeDataUpdateCoordinator,
        address: str,
        entity_description: ButtonEntityDescription,
        action: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._action = action
        self._address = address
        self._attr_unique_id = f"{address}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            name="Nescafe Barista",
            manufacturer=MANUFACTURER,
            model="Gold Blend Barista Slim (SPM9640)",
        )

    async def async_press(self) -> None:
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
            await self._execute_action(client)
        except Exception:
            _LOGGER.exception("Failed to execute action %s", self._action)
        finally:
            await client.disconnect()

    async def _execute_action(self, client: NescafeBleClient) -> None:
        action = self._action

        if action == "espresso":
            await client.start_espresso()
        elif action == "lungo":
            await client.start_lungo()
        elif action == "extra_lungo":
            await client.start_extra_lungo()
        elif action == "cappuccino":
            await client.start_cappuccino()
        elif action == "latte_macchiato":
            await client.start_latte_macchiato()
        elif action == "rinse":
            await client.start_rinse()
        elif action == "hot_water":
            await client.start_hot_water()
        elif action == "custom_recipe":
            await client.start_custom_recipe()
        elif action == "pair":
            await client.perform_pairing()
        elif action == "factory_reset":
            await client.factory_reset()
        elif action == "descale":
            await client.set_descaling_mode()
        elif action == "sync_time":
            await client.set_machine_time()
        elif action == "eco_mode":
            await client.toggle_eco_mode()
