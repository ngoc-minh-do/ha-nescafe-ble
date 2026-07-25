from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from .const import MANUFACTURER


def device_info(address: str, model: str = "Nescafe Barista") -> DeviceInfo:
    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, address)},
        name="Nescafe Barista",
        manufacturer=MANUFACTURER,
        model=model,
    )
