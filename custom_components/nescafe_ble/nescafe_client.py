"""Nescafé Barista BLE client for Home Assistant."""

from __future__ import annotations

import asyncio
import logging
import struct
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

_LOGGER = logging.getLogger(__name__)
_local_tz = datetime.now().astimezone().tzinfo

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


@dataclass(slots=True)
class MachineStatus:
    error_code: int = 0
    machine_state: int = 255
    peripheral_state: int = 0
    leds_on: int = 0
    leds_blink: int = 0

    MACHINE_STATES: ClassVar[dict[int, str]] = {
        0: "init",
        1: "sleep",
        2: "preheat",
        3: "ready",
        4: "extract",
        5: "exception",
        6: "fault",
        255: "unknown",
    }

    ERROR_FLAGS: ClassVar[list[str]] = [
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

    PERIPHERAL_FLAGS: ClassVar[list[str]] = [
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


@dataclass(slots=True)
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


@dataclass(slots=True)
class MachineInfo:
    serial: str = ""
    model: str = ""
    fw_version: str = ""
    sw_version: str = ""
    manufacturer: str = ""


@dataclass(slots=True)
class NescafeData:
    status: MachineStatus | None = None
    counters: MachineCounters | None = None
    coffee_level: int | None = None
    info: MachineInfo | None = None
    machine_time: datetime | None = None
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
        self._client = await establish_connection(
            BleakClient,
            self._ble_device,
            self._ble_device.address,
            timeout=timeout,
        )

    async def disconnect(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def _read_char(self, uuid: str) -> bytearray:
        assert self._client is not None
        return await self._client.read_gatt_char(uuid)

    async def _write_char(self, uuid: str, data: bytes) -> None:
        assert self._client is not None
        await self._client.write_gatt_char(uuid, data, response=True)

    async def _start_notify(self, uuid: str) -> asyncio.Queue[bytearray]:
        assert self._client is not None
        q: asyncio.Queue[bytearray] = asyncio.Queue()

        def handler(_char: Any, data: bytearray) -> None:
            q.put_nowait(bytearray(data))

        await self._client.start_notify(uuid, handler)
        return q

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
            _LOGGER.exception("Failed to read machine serial")

        try:
            data = await self._read_char(CHAR_MODEL_NUMBER)
            info.model = _null_terminated_string(data)
        except Exception:
            _LOGGER.exception("Failed to read model number")

        try:
            data = await self._read_char(CHAR_FW_VERSION)
            info.fw_version = _null_terminated_string(data)
        except Exception:
            _LOGGER.exception("Failed to read firmware version")

        try:
            data = await self._read_char(CHAR_SW_VERSION)
            info.sw_version = _null_terminated_string(data)
        except Exception:
            _LOGGER.exception("Failed to read software version")

        try:
            data = await self._read_char(CHAR_MANUFACTURER_NAME)
            info.manufacturer = _null_terminated_string(data)
        except Exception:
            _LOGGER.exception("Failed to read manufacturer name")
        return info

    async def get_machine_time(self) -> datetime | None:
        data = await self._read_char(CHAR_MACHINE_TIME)
        ts = struct.unpack_from("<I", data, 0)[0]
        if ts == 0:
            return None
        return datetime.fromtimestamp(ts, tz=_local_tz)

    async def set_machine_time(self) -> None:
        import time

        ts = int(time.time())
        data = struct.pack("<I", ts)
        await self._write_char(CHAR_MACHINE_TIME, data)

    async def get_machine_name(self) -> str:
        data = await self._read_char(CHAR_MACHINE_NAME)
        return _null_terminated_string(data)

    async def get_pairing_status(self) -> bool:
        data = await self._read_char(CHAR_BARISTA_STATUS)
        peripheral_state = struct.unpack_from("<H", data, 5)[0]
        return (peripheral_state >> 7) & 1 != 0

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
        result["_rfu"] = list(data[35:45])
        return result

    async def fetch_all(self) -> NescafeData:
        data = NescafeData()
        data.status = await self.get_status()
        try:
            data.counters = await self.get_counters()
        except Exception:
            _LOGGER.exception("Failed to fetch counters")

        try:
            data.coffee_level = await self.get_coffee_level()
        except Exception:
            _LOGGER.exception("Failed to fetch coffee level")

        try:
            data.info = await self.get_info()
        except Exception:
            _LOGGER.exception("Failed to fetch machine info")

        try:
            data.machine_time = await self.get_machine_time()
        except Exception:
            _LOGGER.exception("Failed to fetch machine time")

        try:
            data.pairing_status = await self.get_pairing_status()
        except Exception:
            _LOGGER.exception("Failed to fetch pairing status")

        try:
            data.machine_name = await self.get_machine_name()
        except Exception:
            _LOGGER.exception("Failed to fetch machine name")
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

    async def perform_pairing(self) -> bool:
        from Crypto.Cipher import AES

        q = await self._start_notify(CHAR_MACHINE_SERIAL)

        _LOGGER.debug("Reading status to trigger token notification...")
        await self._read_char(CHAR_BARISTA_STATUS)
        encrypted_token = await asyncio.wait_for(q.get(), timeout=10.0)
        _LOGGER.debug("Encrypted token received (%d bytes)", len(encrypted_token))

        pairing_msg = "WE START PAIRING".encode("ascii").ljust(16, b"\x00")[:16]
        await self._write_char(CHAR_MACHINE_SERIAL, pairing_msg)
        encrypted_password = await asyncio.wait_for(q.get(), timeout=10.0)
        _LOGGER.debug("Encrypted password received (%d bytes)", len(encrypted_password))

        _LOGGER.info("Press the button on the machine within 10 seconds...")
        aes_key = await asyncio.wait_for(q.get(), timeout=15.0)
        _LOGGER.debug("AES key received (%d bytes)", len(aes_key))

        cipher = AES.new(bytes(aes_key), AES.MODE_ECB)
        token = cipher.decrypt(bytes(encrypted_token))
        password = cipher.decrypt(bytes(encrypted_password))
        pairing_key = bytes(a ^ b for a, b in zip(token, password))

        encrypted_key = cipher.encrypt(pairing_key)
        await self._write_char(CHAR_MACHINE_SERIAL, encrypted_key)

        assert self._client is not None
        await self._client.stop_notify(CHAR_MACHINE_SERIAL)

        await asyncio.sleep(1.0)
        paired = await self.get_pairing_status()
        if paired:
            _LOGGER.info("Pairing successful")
        else:
            _LOGGER.warning("Pairing may have failed — machine not reporting paired")
        return paired

    async def factory_reset(self) -> None:
        await self._write_char(CHAR_PARAMETER_BITS_PAIRED, bytes([0x04]))

    async def set_descaling_mode(self) -> None:
        await self._write_char(CHAR_PARAMETER_BITS_PAIRED, bytes([0x02]))
