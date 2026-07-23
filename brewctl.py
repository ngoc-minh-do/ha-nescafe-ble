#!/usr/bin/env python3
"""
brewctl.py - Nescafé Gold Blend Barista Slim (SPM9640) BLE controller.

Compatible with Barista Mini machines using BLE service UUID:
  C08B0100-6407-4A30-8AAB-CCBBAE8B7A4A

Usage:
  brewctl.py scan                    # Scan for nearby machines
  brewctl.py status <mac>            # Read machine status
  brewctl.py brew <mac> <recipe>     # Start a recipe (espresso/lungo/cappuccino/etc.)
  brewctl.py power <mac>             # Toggle power on/off
  brewctl.py info <mac>              # Read machine info (serial, FW, model)
  brewctl.py counters <mac>          # Read usage counters
  brewctl.py coffee-level <mac>      # Read coffee bean level
  brewctl.py pair <mac>              # Pair with machine
  brewctl.py custom-recipe <mac>     # Send a custom recipe
  brewctl.py set-time <mac>          # Sync machine time
"""

import argparse
import asyncio
import logging
import struct
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from bleak import BleakScanner, BleakClient

logger = logging.getLogger("brewctl")

# ── BLE UUIDs ──────────────────────────────────────────────────────────────────

UUID_BASE = "-6407-4A30-8AAB-CCBBAE8B7A4A"
BLE_BASE = "-0000-1000-8000-00805F9B34FB"

SCAN_SERVICE_UUID = "C08B0100" + UUID_BASE

SERVICE_BARISTA_1 = "C08B0100" + UUID_BASE
SERVICE_BARISTA_2 = "C08B0101" + UUID_BASE
SERVICE_BARISTA_3 = "C08B0102" + UUID_BASE
SERVICE_FT = "43AF0000-5C58-4180-A3E4-471D6A45E2DE"
SERVICE_WIFI = "82F21930-F300-4E71-B5F5-714578020395"
SERVICE_FOTA = "167E3128-A9FF-11E9-A2A3-2A2AE2DBCCE4"
SERVICE_DEVICE_INFO = "0000180A" + BLE_BASE

CHAR_BARISTA_STATUS = "C08B0104" + UUID_BASE
CHAR_COUNTERS = "C08B0105" + UUID_BASE
CHAR_EXTRACTION_LOGS = "C08B0106" + UUID_BASE
CHAR_HMI_BUTTON_REQUEST = "C08B0107" + UUID_BASE
CHAR_MACHINE_SERIAL = "C08B0108" + UUID_BASE
CHAR_MACHINE_TIME = "C08B010A" + UUID_BASE
CHAR_PARAMETER_BITS_CONNECTED = "C08B010B" + UUID_BASE
CHAR_BLE_LED_COMMAND = "C08B010C" + UUID_BASE
CHAR_PARAMETER_BITS_PAIRED = "C08B010D" + UUID_BASE
CHAR_RECIPES = "C08B010E" + UUID_BASE
CHAR_CUSTOM_RECIPE = "C08B010F" + UUID_BASE
CHAR_FT_MOTOR = "C08B0110" + UUID_BASE
CHAR_FT_INFO = "C08B0111" + UUID_BASE
CHAR_MACHINE_NAME = "C08B0112" + UUID_BASE
CHAR_COFFEE_LEVEL_RAW = "C08B0113" + UUID_BASE
CHAR_COMMANDS = "43AF0001-5C58-4180-A3E4-471D6A45E2DE"
CHAR_FOTA_COMMANDS = "167E3129-A9FF-11E9-A2A3-2A2AE2DBCCE4"
CHAR_FOTA_STATUS = "167E312A-A9FF-11E9-A2A3-2A2AE2DBCCE4"
CHAR_MODEL_NUMBER = "00002A24" + BLE_BASE
CHAR_FW_VERSION = "00002A26" + BLE_BASE
CHAR_SW_VERSION = "00002A28" + BLE_BASE
CHAR_MANUFACTURER_NAME = "00002A29" + BLE_BASE
CHAR_SYSTEM_ID = "00002A23" + BLE_BASE
CHAR_WIFI_CURRENT_SETTING = "82F21932-F300-4E71-B5F5-714578020395"
CHAR_WIFI_MAC_ADDRESS = "82F21935-F300-4E71-B5F5-714578020395"
CHAR_WIFI_SCAN_SELECTION = "82F21933-F300-4E71-B5F5-714578020395"
CHAR_WIFI_SCAN_SSID = "82F21934-F300-4E71-B5F5-714578020395"
CHAR_WIFI_SETTINGS_SETUP = "82F21931-F300-4E71-B5F5-714578020395"

CLIENT_CHAR_CONFIG = "00002902" + BLE_BASE

# ── Data Models ────────────────────────────────────────────────────────────────


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
        "dosingUnitDirty",
        "mandatoryRinse",
        "lowCoffee",
        "noWaterAlarm",
        "coffeeEmpty",
        "coffeeBoxMissing",
        "drawerOpen",
        "motorBlocked",
        "coffeeLevelSensorMissing",
        "preheat",
        "maxPumpOnTimeExceeded",
        "nTCBroken",
        "overHeating",
        "restSwitchNotConnected",
        "restSwitchTimeout",
        "activeSwitchTimeout",
        "valveSwitchTimeout",
        "motorNotConnected",
        "motorGearboxBroken",
    ]

    PERIPHERAL_FLAGS = [
        "motorOn",
        "valveJetOn",
        "heatOn",
        "pumpOn",
        "fanOn",
        "ambassadorMode",
        "ecoMode",
        "machinePaired",
        "notUsedPaymentMode",
    ]

    LED_FLAGS = [
        "redLed",
        "greenLed",
        "espresso",
        "lungo",
        "extraLungo",
        "cappuccino",
        "latteMacchiato",
        "rinse",
        "noWater",
        "coffeeBeanGreen",
        "coffeeBeanRed",
        "bLE",
        "wifi",
        "hotWater",
    ]

    @property
    def state_name(self) -> str:
        return self.MACHINE_STATES.get(self.machine_state, "unknown")

    @property
    def active_errors(self) -> list[str]:
        return _bitfield_names(self.error_code, self.ERROR_FLAGS)

    @property
    def active_peripherals(self) -> list[str]:
        return _bitfield_names(self.peripheral_state, self.PERIPHERAL_FLAGS)

    @property
    def active_leds(self) -> list[str]:
        return _bitfield_names(self.leds_on, self.LED_FLAGS)

    @property
    def blinking_leds(self) -> list[str]:
        return _bitfield_names(self.leds_blink, self.LED_FLAGS)


@dataclass
class Counters:
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
class CustomRecipe:
    led_index: int = 0
    doses: int = 1
    mixing_volume: int = 40
    jet_volume: int = 0


@dataclass
class ScanResult:
    address: str
    name: str
    rssi: int = 0


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _bitfield_names(value: int, names: list[str]) -> list[str]:
    return [name for i, name in enumerate(names) if (value >> i) & 1]


def _null_terminated_string(data: bytearray | bytes) -> str:
    if isinstance(data, bytearray):
        data = bytes(data)
    null_pos = data.find(b"\x00")
    if null_pos >= 0:
        data = data[:null_pos]
    return data.decode("utf-8", errors="replace")


# ── BLE Machine Client ─────────────────────────────────────────────────────────


class BaristaClient:
    def __init__(self, address: str):
        self.address = address
        self._client: Optional[BleakClient] = None
        self._notify_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, timeout: float = 15.0):
        logger.info(f"Connecting to {self.address} ...")
        self._client = BleakClient(
            self.address,
            timeout=timeout,
            disconnected_callback=self._on_disconnect,
        )
        await self._client.connect()
        logger.info("Connected")

    async def disconnect(self):
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            logger.info("Disconnected")

    def _on_disconnect(self, client: BleakClient):
        logger.warning("Device disconnected")

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    # ── Low-level BLE ops ──────────────────────────────────────────────────

    async def _read_char(self, uuid: str) -> bytearray:
        return await self._client.read_gatt_char(uuid)

    async def _write_char(self, uuid: str, data: bytes):
        await self._client.write_gatt_char(uuid, data, response=True)

    async def _write_char_no_response(self, uuid: str, data: bytes):
        await self._client.write_gatt_char(uuid, data, response=False)

    async def _start_notify(self, uuid: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()

        def handler(_char, data):
            q.put_nowait(bytearray(data))

        await self._client.start_notify(uuid, handler)
        return q

    # ── Status ─────────────────────────────────────────────────────────────

    async def get_status(self) -> MachineStatus:
        data = await self._read_char(CHAR_BARISTA_STATUS)
        return MachineStatus(
            error_code=struct.unpack_from("<I", data, 0)[0],
            machine_state=data[4] & 0xFF,
            peripheral_state=struct.unpack_from("<H", data, 5)[0],
            leds_on=struct.unpack_from("<H", data, 7)[0],
            leds_blink=struct.unpack_from("<H", data, 9)[0],
        )

    # ── Counters ───────────────────────────────────────────────────────────

    async def get_counters(self) -> Counters:
        data = await self._read_char(CHAR_COUNTERS)
        return Counters(
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

    # ── Coffee Level ───────────────────────────────────────────────────────

    async def get_coffee_level(self) -> int:
        data = await self._read_char(CHAR_COFFEE_LEVEL_RAW)
        return struct.unpack_from("<H", data, 0)[0]

    # ── Machine Info ───────────────────────────────────────────────────────

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

    # ── Machine Time ───────────────────────────────────────────────────────

    async def get_machine_time(self) -> Optional[datetime]:
        data = await self._read_char(CHAR_MACHINE_TIME)
        ts = struct.unpack_from("<I", data, 0)[0]
        if ts == 0:
            return None
        return datetime.fromtimestamp(ts)

    async def set_machine_time(self):
        ts = int(time.time())
        data = struct.pack("<I", ts)
        await self._write_char(CHAR_MACHINE_TIME, data)
        logger.info(f"Machine time set to {datetime.fromtimestamp(ts)}")

    # ── Machine Name ───────────────────────────────────────────────────────

    async def get_machine_name(self) -> str:
        data = await self._read_char(CHAR_MACHINE_NAME)
        return _null_terminated_string(data)

    async def set_machine_name(self, name: str):
        name_bytes = name.encode("utf-8")[:20]
        await self._write_char(CHAR_MACHINE_NAME, name_bytes)
        logger.info(f"Machine name set to '{name}'")

    # ── HMI Button Requests (brew commands) ────────────────────────────────

    async def _send_hmi_button(self, byte0: int, byte1: int):
        data = bytes([byte0 & 0xFF, byte1 & 0xFF])
        await self._write_char(CHAR_HMI_BUTTON_REQUEST, data)

    async def power_on_off(self):
        await self._send_hmi_button(0x00, 0x01)

    async def start_espresso(self):
        await self._send_hmi_button(0x00, 0x08)

    async def start_lungo(self):
        await self._send_hmi_button(0x00, 0x10)

    async def start_extra_lungo(self):
        await self._send_hmi_button(0x00, 0x20)

    async def start_cappuccino(self):
        await self._send_hmi_button(0x00, 0x40)

    async def start_latte_macchiato(self):
        await self._send_hmi_button(0x00, 0x80)

    async def start_rinse(self):
        await self._send_hmi_button(0x00, 0x04)

    async def start_hot_water(self):
        await self._send_hmi_button(0x01, 0x00)

    async def start_custom_recipe(self):
        await self._send_hmi_button(0x00, 0x02)

    async def toggle_eco_mode(self):
        await self._send_hmi_button(0x02, 0x00)

    RECIPE_MAP = {
        "espresso": start_espresso,
        "lungo": start_lungo,
        "extralungo": start_extra_lungo,
        "cappuccino": start_cappuccino,
        "lattemacchiato": start_latte_macchiato,
        "rinse": start_rinse,
        "hotwater": start_hot_water,
        "custom": start_custom_recipe,
        "power": power_on_off,
        "eco": toggle_eco_mode,
    }

    async def start_recipe(self, recipe: str):
        handler = self.RECIPE_MAP.get(recipe.lower())
        if handler is None:
            valid = ", ".join(self.RECIPE_MAP.keys())
            raise ValueError(f"Unknown recipe '{recipe}'. Valid: {valid}")
        await handler(self)

    # ── Custom Recipe ──────────────────────────────────────────────────────

    async def send_custom_recipe(self, recipe: CustomRecipe):
        led = min(max(recipe.led_index, 0), 4)
        doses = min(max(recipe.doses, 1), 5)
        mixing = min(max(recipe.mixing_volume, 40), 300)
        jet = min(max(recipe.jet_volume, 0), 90)

        byte0 = ((led & 0x0F) << 4) | (doses & 0x0F)
        byte1 = (mixing >> 8) & 0xFF
        byte2 = mixing & 0xFF
        byte3 = (jet >> 8) & 0xFF
        byte4 = jet & 0xFF

        data = bytes([byte0, byte1, byte2, byte3, byte4])
        await self._write_char(CHAR_CUSTOM_RECIPE, data)
        logger.info(
            f"Custom recipe sent: LED={led}, Doses={doses}, "
            f"Mixing={mixing}ml, Jet={jet}ml"
        )

    # ── Recipes (standard) ─────────────────────────────────────────────────

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

    # ── Pairing ────────────────────────────────────────────────────────────

    async def get_pairing_status(self) -> bool:
        data = await self._read_char(CHAR_PARAMETER_BITS_PAIRED)
        return (data[0] & 0x04) != 0 if data else False

    async def perform_pairing(self):
        logger.info("Initiating pairing with 'WE START PAIRING' ...")
        pairing_bytes = "WE START PAIRING".encode("ascii")
        await self._write_char(
            CHAR_MACHINE_SERIAL, pairing_bytes.ljust(16, b"\x00")[:16]
        )
        logger.info(
            "Pairing initiation sent. Press the button on your machine if needed."
        )

    # ── Factory Reset / Descaling ──────────────────────────────────────────

    async def factory_reset(self):
        await self._write_char(CHAR_PARAMETER_BITS_PAIRED, bytes([0x04]))

    async def set_descaling_mode(self):
        await self._write_char(CHAR_PARAMETER_BITS_PAIRED, bytes([0x02]))

    # ── BLE LED ────────────────────────────────────────────────────────────

    async def set_led(self, mode: int):
        await self._write_char(CHAR_BLE_LED_COMMAND, bytes([mode & 0xFF]))


# ── Scanner ─────────────────────────────────────────────────────────────────────


async def scan_machines(timeout: float = 5.0) -> list[ScanResult]:
    logger.info(f"Scanning for Barista Mini machines (timeout={timeout}s) ...")
    results: list[ScanResult] = []

    def callback(device, advertisement_data):
        for uuid in advertisement_data.service_uuids or []:
            if uuid.lower().startswith("c08b0100"):
                results.append(
                    ScanResult(
                        address=device.address,
                        name=device.name or advertisement_data.local_name or "???",
                        rssi=advertisement_data.rssi or 0,
                    )
                )
                break

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    return results


# ── CLI ─────────────────────────────────────────────────────────────────────────


def _setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def _print_status(status: MachineStatus):
    print(f"Machine State:  {status.state_name} ({status.machine_state})")
    print(f"Errors:         {', '.join(status.active_errors) or 'none'}")
    print(f"Peripherals:    {', '.join(status.active_peripherals) or 'none'}")
    print(f"LEDs On:        {', '.join(status.active_leds) or 'none'}")
    print(f"LEDs Blink:     {', '.join(status.blinking_leds) or 'none'}")


def _print_counters(counters: Counters):
    print(f"Espresso:       {counters.espresso}")
    print(f"Lungo:          {counters.lungo}")
    print(f"Extra Lungo:    {counters.extra_lungo}")
    print(f"Cappuccino:     {counters.cappuccino}")
    print(f"Latte Macch.:   {counters.latte_macchiato}")
    print(f"Hot Water:      {counters.hot_water}")
    print(f"Rinse:          {counters.rinse}")
    print(f"Custom Recipe:  {counters.custom_recipe}")
    print(f"Motor Blocked:  {counters.motor_blocked}")
    print(f"Motor Dirty:    {counters.motor_dirty}")
    print(f"No Water:       {counters.no_water}")


def _print_info(info: MachineInfo):
    print(f"Serial:         {info.serial or 'n/a'}")
    print(f"Model:          {info.model or 'n/a'}")
    print(f"FW Version:     {info.fw_version or 'n/a'}")
    print(f"SW Version:     {info.sw_version or 'n/a'}")
    print(f"Manufacturer:   {info.manufacturer or 'n/a'}")


async def _cmd_scan(_args):
    machines = await scan_machines(timeout=_args.timeout)
    if not machines:
        print("No Barista Mini machines found.")
        return
    print(f"Found {len(machines)} machine(s):")
    for m in machines:
        print(f"  {m.address}  RSSI={m.rssi:4d}dBm  {m.name}")


async def _cmd_status(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        status = await c.get_status()
        _print_status(status)
    finally:
        await c.disconnect()


async def _cmd_counters(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        counters = await c.get_counters()
        _print_counters(counters)
    finally:
        await c.disconnect()


async def _cmd_info(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        info = await c.get_info()
        _print_info(info)
    finally:
        await c.disconnect()


async def _cmd_coffee_level(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        level = await c.get_coffee_level()
        print(f"Coffee Level Raw: {level}")
    finally:
        await c.disconnect()


async def _cmd_brew(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        await c.start_recipe(args.recipe)
        print(f"Started: {args.recipe}")
    finally:
        await c.disconnect()


async def _cmd_power(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        await c.power_on_off()
        print("Power toggled.")
    finally:
        await c.disconnect()


async def _cmd_pair(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        await c.perform_pairing()
    finally:
        await c.disconnect()


async def _cmd_custom_recipe(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        recipe = CustomRecipe(
            led_index=args.led,
            doses=args.doses,
            mixing_volume=args.mixing,
            jet_volume=args.jet,
        )
        await c.send_custom_recipe(recipe)
        await c.start_custom_recipe()
        print("Custom recipe started.")
    finally:
        await c.disconnect()


async def _cmd_set_time(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        before = await c.get_machine_time()
        await c.set_machine_time()
        after = await c.get_machine_time()
        print(f"Time before: {before or 'unset'}")
        print(f"Time after:  {after or 'unset'}")
    finally:
        await c.disconnect()


async def _cmd_recipes(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        recipes = await c.get_recipes()
        for name, data in recipes.items():
            print(f"  {name:20s} {[int(b) for b in data]}")
    finally:
        await c.disconnect()


async def _cmd_factory_reset(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        await c.factory_reset()
        print("Factory reset command sent.")
    finally:
        await c.disconnect()


async def _cmd_descale(args):
    c = BaristaClient(args.mac)
    try:
        await c.connect()
        await c.set_descaling_mode()
        print("Descaling mode set.")
    finally:
        await c.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Nescafé Barista Mini BLE Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  %(prog)s scan
  %(prog)s status AA:BB:CC:DD:EE:FF
  %(prog)s brew AA:BB:CC:DD:EE:FF espresso
  %(prog)s power AA:BB:CC:DD:EE:FF
  %(prog)s info AA:BB:CC:DD:EE:FF
        """,
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug output"
    )

    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="Scan for machines")
    p_scan.add_argument("-t", "--timeout", type=float, default=5.0)

    p_status = sub.add_parser("status", help="Read machine status")
    p_status.add_argument("mac", help="Machine MAC address")

    p_counters = sub.add_parser("counters", help="Read usage counters")
    p_counters.add_argument("mac", help="Machine MAC address")

    p_info = sub.add_parser("info", help="Read machine info")
    p_info.add_argument("mac", help="Machine MAC address")

    p_coffee = sub.add_parser("coffee-level", help="Read coffee level")
    p_coffee.add_argument("mac", help="Machine MAC address")

    p_brew = sub.add_parser("brew", help="Start a recipe")
    p_brew.add_argument("mac", help="Machine MAC address")
    p_brew.add_argument(
        "recipe",
        choices=list(BaristaClient.RECIPE_MAP.keys()),
        help="Recipe to brew",
    )

    p_power = sub.add_parser("power", help="Toggle power on/off")
    p_power.add_argument("mac", help="Machine MAC address")

    p_pair = sub.add_parser("pair", help="Pair with machine")
    p_pair.add_argument("mac", help="Machine MAC address")

    p_custom = sub.add_parser("custom-recipe", help="Send and brew custom recipe")
    p_custom.add_argument("mac", help="Machine MAC address")
    p_custom.add_argument("--led", type=int, default=0, help="LED index (0-4)")
    p_custom.add_argument("--doses", type=int, default=1, help="Doses (1-5)")
    p_custom.add_argument(
        "--mixing", type=int, default=40, help="Mixing volume ml (40-300)"
    )
    p_custom.add_argument("--jet", type=int, default=0, help="Jet volume ml (0-90)")

    p_settime = sub.add_parser("set-time", help="Sync machine time")
    p_settime.add_argument("mac", help="Machine MAC address")

    p_recipes = sub.add_parser("recipes", help="Read standard recipes")
    p_recipes.add_argument("mac", help="Machine MAC address")

    p_factory = sub.add_parser("factory-reset", help="Factory reset machine")
    p_factory.add_argument("mac", help="Machine MAC address")

    p_descale = sub.add_parser("descale", help="Set descaling mode")
    p_descale.add_argument("mac", help="Machine MAC address")

    args = parser.parse_args()
    _setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "scan": _cmd_scan,
        "status": _cmd_status,
        "counters": _cmd_counters,
        "info": _cmd_info,
        "coffee-level": _cmd_coffee_level,
        "brew": _cmd_brew,
        "power": _cmd_power,
        "pair": _cmd_pair,
        "custom-recipe": _cmd_custom_recipe,
        "set-time": _cmd_set_time,
        "recipes": _cmd_recipes,
        "factory-reset": _cmd_factory_reset,
        "descale": _cmd_descale,
    }

    handler = commands.get(args.command)
    if handler:
        asyncio.run(handler(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
