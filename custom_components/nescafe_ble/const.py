"""Constants for the Nescafe BLE integration."""

DOMAIN = "nescafe_ble"
MANUFACTURER = "Nescafé / De'Longhi"

CONF_ADDRESS = "address"

SCAN_SERVICE_UUID = "C08B0100-6407-4A30-8AAB-CCBBAE8B7A4A"

DEFAULT_SCAN_INTERVAL = 60

MACHINE_STATE_SENSOR = "machine_state"
COFFEE_LEVEL_SENSOR = "coffee_level"
COUNTER_SENSORS = [
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
]

RECIPE_BUTTONS = {
    "espresso": "Brew Espresso",
    "lungo": "Brew Lungo",
    "extra_lungo": "Brew Extra Lungo",
    "cappuccino": "Brew Cappuccino",
    "latte_macchiato": "Brew Latte Macchiato",
    "rinse": "Rinse",
    "hot_water": "Hot Water",
    "custom_recipe": "Custom Recipe",
}

ACTION_BUTTONS = {
    "pair": "Pair",
    "factory_reset": "Factory Reset",
    "descale": "Descale",
    "sync_time": "Sync Time",
    "eco_mode": "Eco Mode",
}
