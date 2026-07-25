"""Binary sensor platform for Nescafe BLE error flags."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import NescafeDataUpdateCoordinator
from .device import device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import NescafeConfigEntry

_LOGGER = logging.getLogger(__name__)

ERROR_BINARY_SENSORS: dict[str, BinarySensorEntityDescription] = {
    "dosing_unit_dirty": BinarySensorEntityDescription(
        key="dosing_unit_dirty",
        translation_key="dosing_unit_dirty",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "mandatory_rinse": BinarySensorEntityDescription(
        key="mandatory_rinse",
        translation_key="mandatory_rinse",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "low_coffee": BinarySensorEntityDescription(
        key="low_coffee",
        translation_key="low_coffee",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "no_water": BinarySensorEntityDescription(
        key="no_water",
        translation_key="no_water_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "coffee_empty": BinarySensorEntityDescription(
        key="coffee_empty",
        translation_key="coffee_empty",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "coffee_box_missing": BinarySensorEntityDescription(
        key="coffee_box_missing",
        translation_key="coffee_box_missing",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "drawer_open": BinarySensorEntityDescription(
        key="drawer_open",
        translation_key="drawer_open",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "motor_blocked": BinarySensorEntityDescription(
        key="motor_blocked",
        translation_key="motor_blocked_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "coffee_level_sensor_missing": BinarySensorEntityDescription(
        key="coffee_level_sensor_missing",
        translation_key="coffee_level_sensor_missing",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "over_heating": BinarySensorEntityDescription(
        key="over_heating",
        translation_key="over_heating",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
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

    entities: list[NescafeBinarySensor] = []
    for description in ERROR_BINARY_SENSORS.values():
        entities.append(NescafeBinarySensor(coordinator, address, model, description))

    async_add_entities(entities)


class NescafeBinarySensor(
    CoordinatorEntity[NescafeDataUpdateCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NescafeDataUpdateCoordinator,
        address: str,
        model: str,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{address}_{entity_description.key}"
        self._attr_device_info = device_info(address, model)

    @property
    @override
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None or data.status is None:
            return None
        return self.entity_description.key in data.status.active_errors
