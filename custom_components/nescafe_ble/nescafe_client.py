"""Nescafé Barista BLE client for Home Assistant."""

import struct
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from bleak import BleakClient
from bleak.backends.device import BLEDevice

UUID_BASE = "-6407-4A30-8AAB-CCBBAE8B7A4A"
BLE_BASE = "-0000-1000-8000-00805F9B34FB"

SERVICE_BARISTA = "C08B0100" + UUID_BASE

CHAR_BARISTA_STATUS = "C08B0104" + UUID_BASE
CHAR_COUNTERS = "C08B0105" + UUID_BASE
CHAR_MACHINE_SERIAL = "C08B0108" + UUID_BASE
CHAR_MACHINE_TIME = "C08B010A" + UUID_BASE
CHAR_PARAMETER_BITS_PAIRED = "C08B010D" + UUID_BASE
CHAR_RECIPES = "C08B010E" + UUID_BASE
CHAR_CUSTOM_RECIPE = "C08B010F" + UUID_BASE
CHAR_MACHINE_NAME = "C08B0112" + UUID_BASE
CHAR_COFFEE_LEVEL_RAW = "C08B0113" + UUID_BASE
CHAR_HMI_BUTTON_REQUEST = "C08B0107" + UUID_BASE
CHAR_MODEL_NUMBER = "00002A24" + BLE_BASE
CHAR_FW_VERSION = "00002A26" + BLE_BASE
CHAR_SW_VERSION = "00002A28" + BLE_BASE
CHAR_MANUFACTURER_NAME = "00002A29" + BLE_BASE


@dataclass
class MachineStatus:
    error_code: int = 0
    machine_state: int = 255
    peripheral_state: int = 0
    leds_on: int = 0
    leds_blink: int = 0

    MACHINE_STATES = {
        0: "init",
        1: "sleep",
        2: "preheat",
        3: "ready",
        4: "extract",
        5: "exception",
        6: "fault",
        255: "unknown",
    }

    ERROR_FLAGS = [
        "dosing_unit_dirty",
        "mandatory_rinse",
        "low_coffee",
        "no_water",
        "coffee_empty",
        "coffee_box_missing",
        "drawer_open",
        "motor_blocked",
        "coffee_level_sensor_missing",
        "preheat_error",
        "max_pump_on_time_exceeded",
        "ntc_broken",
        "over_heating",
        "rest_switch_not_connected",
        "rest_switch_timeout",
        "active_switch_timeout",
        "valve_switch_timeout",
        "motor_not_connected",
        "motor_gearbox_broken",
    ]

    PERIPHERAL_FLAGS = [
        "motor_on",
        "valve_jet_on",
        "heat_on",
        "pump_on",
        "fan_on",
        "ambassador_mode",
        "eco_mode",
        "machine_paired",
        "not_used_payment_mode",
    ]

    @property
    def state_name(self) -> str:
        return self.MACHINE_STATES.get(self.machine_state, "unknown")

    @property
    def active_errors(self) -> list[str]:
        return [n for i, n in enumerate(self.ERROR_FLAGS) if (self.error_code >> i) & 1]

    @property
    def active_peripherals(self) -> list[str]:
        return [
            n
            for i, n in enumerate(self.PERIPHERAL_FLAGS)
            if (self.peripheral_state >> i) & 1
        ]


@dataclass
class MachineCounters:
    motor_blocked: int = 0
    motor_dirty: int = 0
    no_water: int = 0
    rinse: int = 0
    espresso: int = 0
    lungo: int = 0
    extra_lungo: int = 0
    cappuccino: int = 0
    latte_macchiato: int = 0
    custom_recipe: int = 0
    hot_water: int = 0


@dataclass
class MachineInfo:
    serial: str = ""
    model: str = ""
    fw_version: str = ""
    sw_version: str = ""
    manufacturer: str = ""


@dataclass
class NescafeData:
    status: MachineStatus | None = None
    counters: MachineCounters | None = None
    coffee_level: int | None = None
    info: MachineInfo | None = None
    machine_time: Optional[datetime] = None
    pairing_status: bool | None = None
    machine_name: str | None = None
    recipes: dict[str, list[int]] | None = None


def _null_terminated_string(data: bytearray | bytes) -> str:
    if isinstance(data, bytearray):
        data = bytes(data)
    null_pos = data.find(b"\x00")
    if null_pos >= 0:
        data = data[:null_pos]
    return data.decode("utf-8", errors="replace")


class NescafeBleClient:
    def __init__(self, ble_device: BLEDevice):
        self._ble_device = ble_device
        self._client: BleakClient | None = None

    async def connect(self, timeout: float = 15.0) -> None:
        self._client = BleakClient(
            self._ble_device,
            timeout=timeout,
        )
        await self._client.connect()

    async def disconnect(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def _read_char(self, uuid: str) -> bytearray:
        return await self._client.read_gatt_char(uuid)

    async def _write_char(self, uuid: str, data: bytes) -> None:
        await self._client.write_gatt_char(uuid, data, response=True)

    async def get_status(self) -> MachineStatus:
        data = await self._read_char(CHAR_BARISTA_STATUS)
        return MachineStatus(
            error_code=struct.unpack_from("<I", data, 0)[0],
            machine_state=data[4] & 0xFF,
            peripheral_state=struct.unpack_from("<H", data, 5)[0],
            leds_on=struct.unpack_from("<H", data, 7)[0],
            leds_blink=struct.unpack_from("<H", data, 9)[0],
        )

    async def get_counters(self) -> MachineCounters:
        data = await self._read_char(CHAR_COUNTERS)
        return MachineCounters(
            motor_blocked=data[0],
            motor_dirty=data[1],
            no_water=data[2],
            rinse=data[3],
            espresso=struct.unpack_from("<H", data, 4)[0],
            lungo=struct.unpack_from("<H", data, 6)[0],
            extra_lungo=struct.unpack_from("<H", data, 8)[0],
            cappuccino=struct.unpack_from("<H", data, 10)[0],
            latte_macchiato=struct.unpack_from("<H", data, 12)[0],
            custom_recipe=struct.unpack_from("<H", data, 14)[0],
            hot_water=struct.unpack_from("<H", data, 16)[0],
        )

    async def get_coffee_level(self) -> int:
        data = await self._read_char(CHAR_COFFEE_LEVEL_RAW)
        return struct.unpack_from("<H", data, 0)[0]

    async def get_info(self) -> MachineInfo:
        info = MachineInfo()
        try:
            data = await self._read_char(CHAR_MACHINE_SERIAL)
            info.serial = _null_terminated_string(data)
        except Exception:
            pass
        try:
            data = await self._read_char(CHAR_MODEL_NUMBER)
            info.model = _null_terminated_string(data)
        except Exception:
            pass
        try:
            data = await self._read_char(CHAR_FW_VERSION)
            info.fw_version = _null_terminated_string(data)
        except Exception:
            pass
        try:
            data = await self._read_char(CHAR_SW_VERSION)
            info.sw_version = _null_terminated_string(data)
        except Exception:
            pass
        try:
            data = await self._read_char(CHAR_MANUFACTURER_NAME)
            info.manufacturer = _null_terminated_string(data)
        except Exception:
            pass
        return info

    async def get_machine_time(self) -> Optional[datetime]:
        data = await self._read_char(CHAR_MACHINE_TIME)
        ts = struct.unpack_from("<I", data, 0)[0]
        if ts == 0:
            return None
        return datetime.fromtimestamp(ts)

    async def set_machine_time(self) -> None:
        import time

        ts = int(time.time())
        data = struct.pack("<I", ts)
        await self._write_char(CHAR_MACHINE_TIME, data)

    async def get_machine_name(self) -> str:
        data = await self._read_char(CHAR_MACHINE_NAME)
        return _null_terminated_string(data)

    async def get_pairing_status(self) -> bool:
        data = await self._read_char(CHAR_PARAMETER_BITS_PAIRED)
        return (data[0] & 0x04) != 0 if data else False

    async def get_recipes(self) -> dict[str, list[int]]:
        data = await self._read_char(CHAR_RECIPES)
        names = [
            "espresso",
            "lungo",
            "xlungo",
            "cappuccino",
            "latte_macchiato",
            "hot_water",
            "custom",
        ]
        result = {}
        for i, name in enumerate(names):
            offset = i * 5
            result[name] = list(data[offset : offset + 5])
        return result

    async def fetch_all(self) -> NescafeData:
        data = NescafeData()
        data.status = await self.get_status()
        try:
            data.counters = await self.get_counters()
        except Exception:
            pass
        try:
            data.coffee_level = await self.get_coffee_level()
        except Exception:
            pass
        try:
            data.info = await self.get_info()
        except Exception:
            pass
        try:
            data.machine_time = await self.get_machine_time()
        except Exception:
            pass
        try:
            data.pairing_status = await self.get_pairing_status()
        except Exception:
            pass
        try:
            data.machine_name = await self.get_machine_name()
        except Exception:
            pass
        return data

    async def send_hmi_button(self, byte0: int, byte1: int) -> None:
        data = bytes([byte0 & 0xFF, byte1 & 0xFF])
        await self._write_char(CHAR_HMI_BUTTON_REQUEST, data)

    async def start_espresso(self) -> None:
        await self.send_hmi_button(0x00, 0x08)

    async def start_lungo(self) -> None:
        await self.send_hmi_button(0x00, 0x10)

    async def start_extra_lungo(self) -> None:
        await self.send_hmi_button(0x00, 0x20)

    async def start_cappuccino(self) -> None:
        await self.send_hmi_button(0x00, 0x40)

    async def start_latte_macchiato(self) -> None:
        await self.send_hmi_button(0x00, 0x80)

    async def start_rinse(self) -> None:
        await self.send_hmi_button(0x00, 0x04)

    async def start_hot_water(self) -> None:
        await self.send_hmi_button(0x01, 0x00)

    async def start_custom_recipe(self) -> None:
        await self.send_hmi_button(0x00, 0x02)

    async def power_on_off(self) -> None:
        await self.send_hmi_button(0x00, 0x01)

    async def toggle_eco_mode(self) -> None:
        await self.send_hmi_button(0x02, 0x00)

    async def perform_pairing(self) -> None:
        pairing_bytes = "WE START PAIRING".encode("ascii")
        await self._write_char(
            CHAR_MACHINE_SERIAL, pairing_bytes.ljust(16, b"\x00")[:16]
        )

    async def factory_reset(self) -> None:
        await self._write_char(CHAR_PARAMETER_BITS_PAIRED, bytes([0x04]))

    async def set_descaling_mode(self) -> None:
        await self._write_char(CHAR_PARAMETER_BITS_PAIRED, bytes([0x02]))
