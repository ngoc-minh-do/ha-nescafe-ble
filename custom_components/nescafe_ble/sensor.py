"""Sensor platform for Nescafe BLE."""

from __future__ import annotations

import logging
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import MANUFACTURER
from .coordinator import NescafeConfigEntry, NescafeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "machine_state": SensorEntityDescription(
        key="machine_state",
        translation_key="machine_state",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "init",
            "sleep",
            "preheat",
            "ready",
            "extract",
            "exception",
            "fault",
            "unknown",
        ],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "coffee_level": SensorEntityDescription(
        key="coffee_level",
        translation_key="coffee_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    "espresso": SensorEntityDescription(
        key="espresso",
        translation_key="counter_espresso",
        native_unit_of_measurement="brews",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "lungo": SensorEntityDescription(
        key="lungo",
        translation_key="counter_lungo",
        native_unit_of_measurement="brews",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "extra_lungo": SensorEntityDescription(
        key="extra_lungo",
        translation_key="counter_extra_lungo",
        native_unit_of_measurement="brews",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "cappuccino": SensorEntityDescription(
        key="cappuccino",
        translation_key="counter_cappuccino",
        native_unit_of_measurement="brews",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "latte_macchiato": SensorEntityDescription(
        key="latte_macchiato",
        translation_key="counter_latte_macchiato",
        native_unit_of_measurement="brews",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "hot_water": SensorEntityDescription(
        key="hot_water",
        translation_key="counter_hot_water",
        native_unit_of_measurement="uses",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "rinse": SensorEntityDescription(
        key="rinse",
        translation_key="counter_rinse",
        native_unit_of_measurement="uses",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "custom_recipe": SensorEntityDescription(
        key="custom_recipe",
        translation_key="counter_custom_recipe",
        native_unit_of_measurement="brews",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "motor_blocked": SensorEntityDescription(
        key="motor_blocked",
        translation_key="counter_motor_blocked",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "motor_dirty": SensorEntityDescription(
        key="motor_dirty",
        translation_key="counter_motor_dirty",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "no_water": SensorEntityDescription(
        key="no_water",
        translation_key="counter_no_water",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "firmware": SensorEntityDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "model": SensorEntityDescription(
        key="model",
        translation_key="model",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "serial": SensorEntityDescription(
        key="serial",
        translation_key="serial",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "manufacturer": SensorEntityDescription(
        key="manufacturer",
        translation_key="manufacturer",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "machine_name": SensorEntityDescription(
        key="machine_name",
        translation_key="machine_name",
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

    entities: list[NescafeSensor] = []
    for sensor_key in SENSOR_DESCRIPTIONS:
        entities.append(
            NescafeSensor(coordinator, address, SENSOR_DESCRIPTIONS[sensor_key])
        )

    async_add_entities(entities)


class NescafeSensor(CoordinatorEntity[NescafeDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NescafeDataUpdateCoordinator,
        address: str,
        entity_description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{address}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            name="Nescafe Barista",
            manufacturer=MANUFACTURER,
            model="Gold Blend Barista Slim (SPM9640)",
        )

    @property
    @override
    def native_value(self) -> StateType:
        data = self.coordinator.data
        if data is None:
            return None

        key = self.entity_description.key

        if key == "machine_state":
            if data.status is None:
                return None
            return data.status.state_name

        if key == "coffee_level":
            return data.coffee_level

        if key in ("firmware", "model", "serial", "manufacturer", "machine_name"):
            if data.info is None:
                return None
            return getattr(data.info, key, None)

        if key in (
            "espresso",
            "lungo",
            "extra_lungo",
            "cappuccino",
            "latte_macchiato",
            "hot_water",
            "rinse",
            "custom_recipe",
            "motor_blocked",
            "motor_dirty",
            "no_water",
        ):
            if data.counters is None:
                return None
            return getattr(data.counters, key, None)

        return None
