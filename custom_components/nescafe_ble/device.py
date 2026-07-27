from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from .const import MANUFACTURER


def device_info(address: str, model: str = "Nescafe Gold Blend Barista") -> DeviceInfo:
    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, address)},
        name="Nescafe Gold Blend Barista",
        manufacturer=MANUFACTURER,
        model=model,
    )
