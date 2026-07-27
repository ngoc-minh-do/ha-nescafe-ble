"""Button platform for Nescafe BLE."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ACTION_BUTTONS, RECIPE_BUTTONS
from .coordinator import NescafeDataUpdateCoordinator
from .device import device_info
from .nescafe_client import NescafeBleClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import NescafeConfigEntry

_LOGGER = logging.getLogger(__name__)

BUTTON_COOLDOWN = 2.0
_cooldown_until: float = 0.0
_instances: list[NescafeButton] = []


def _update_all_button_states() -> None:
    for btn in _instances:
        btn.async_write_ha_state()


RECIPE_BUTTON_ICONS: dict[str, str] = {
    "espresso": "mdi:cup",
    "lungo": "mdi:coffee",
    "extra_lungo": "mdi:coffee",
    "cappuccino": "mdi:coffee",
    "latte_macchiato": "mdi:coffee",
    "rinse": "mdi:water-sync",
    "hot_water": "mdi:cup-water",
    "custom_recipe": "mdi:coffee-outline",
}

ACTION_BUTTON_ICONS: dict[str, str] = {
    "power_on_off": "mdi:power",
    "pair": "mdi:bluetooth-connect",
    "factory_reset": "mdi:restore-alert",
    "descale": "mdi:water-percent",
    "reset_to_production": "mdi:restore",
    "sync_time": "mdi:clock-outline",
    "eco_mode": "mdi:leaf",
}

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NescafeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    address = entry.unique_id or ""
    model = entry.title

    entities: list[NescafeButton] = []

    for recipe_key, recipe_name in RECIPE_BUTTONS.items():
        entities.append(
            NescafeButton(
                coordinator,
                address,
                model,
                ButtonEntityDescription(
                    key=f"brew_{recipe_key}",
                    translation_key=f"brew_{recipe_key}",
                    name=recipe_name,
                    icon=RECIPE_BUTTON_ICONS.get(recipe_key),
                ),
                recipe_key,
            )
        )

    for action_key, action_name in ACTION_BUTTONS.items():
        if action_key == "power_on_off":
            desc = ButtonEntityDescription(
                key=f"action_{action_key}",
                translation_key=f"action_{action_key}",
                name=action_name,
                icon=ACTION_BUTTON_ICONS.get(action_key),
            )
        else:
            desc = ButtonEntityDescription(
                key=f"action_{action_key}",
                translation_key=f"action_{action_key}",
                name=action_name,
                icon=ACTION_BUTTON_ICONS.get(action_key),
                entity_category=EntityCategory.CONFIG,
            )
        entities.append(NescafeButton(coordinator, address, model, desc, action_key))

    async_add_entities(entities)


class NescafeButton(CoordinatorEntity[NescafeDataUpdateCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NescafeDataUpdateCoordinator,
        address: str,
        model: str,
        entity_description: ButtonEntityDescription,
        action: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._action = action
        self._address = address
        self._attr_unique_id = f"{address}_{entity_description.key}"
        self._attr_device_info = device_info(address, model)
        _instances.append(self)

    @property
    def available(self) -> bool:
        if time.monotonic() < _cooldown_until:
            return False
        if self.coordinator.data is None:
            return False
        return super().available

    async def async_press(self) -> None:
        global _cooldown_until
        if time.monotonic() < _cooldown_until:
            _LOGGER.warning("Button %s ignored: cooldown active", self._action)
            return
        _cooldown_until = time.monotonic() + BUTTON_COOLDOWN
        _update_all_button_states()

        async def _reset_cooldown():
            await asyncio.sleep(BUTTON_COOLDOWN)
            if time.monotonic() >= _cooldown_until:
                _update_all_button_states()

        asyncio.ensure_future(_reset_cooldown())

        from bleak_retry_connector import close_stale_connections_by_address
        from homeassistant.components import bluetooth

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
            await client._try_pair()
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
        elif action == "reset_to_production":
            await client.reset_to_production_mode()
        elif action == "sync_time":
            await client.set_machine_time()
        elif action == "eco_mode":
            await client.toggle_eco_mode()
        elif action == "power_on_off":
            await client.power_on_off()
