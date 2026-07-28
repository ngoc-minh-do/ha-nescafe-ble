"""Constants for the Nescafe BLE integration."""

DOMAIN = "nescafe_ble"
MANUFACTURER = "Nescafé"

CONF_ADDRESS = "address"
CONF_SCAN_INTERVAL = "scan_interval"

SCAN_SERVICE_UUID = "c08b0100-6407-4a30-8aab-ccbbae8b7a4a"

DEFAULT_SCAN_INTERVAL = 86400

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
    "espresso": "Brew Espresso / Iced Coffee",
    "lungo": "Brew Lungo (Black)",
    "extra_lungo": "Brew Large Lungo (Large Black)",
    "cappuccino": "Brew Cappuccino",
    "latte_macchiato": "Brew Latte Macchiato (Cafe Latte)",
    "rinse": "Rinse",
    "hot_water": "Hot Water",
    "custom_recipe": "Custom Recipe",
}

ACTION_BUTTONS = {
    "power_on_off": "Power",
    "pair": "Pair",
    "factory_reset": "Factory Reset",
    "descale": "Descale",
    "reset_to_production": "Reset to Production Mode",
    "sync_time": "Sync Time",
    "eco_mode": "Eco Mode",
}
