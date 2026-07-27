# ha-nescafe-ble

Home Assistant custom integration for Nescafé Gold Blend Barista BLE machines (Barista Mini).

## Features

- **Machine status** — state (sleep/preheat/ready/extract), error flags, peripheral flags
- **Coffee level** — bean hopper level sensor
- **Usage counters** — espresso, lungo, large lungo, cappuccino, latte macchiato, hot water, rinse, custom recipe, motor events
- **Machine info** — serial, model, firmware version, manufacturer
- **Machine time** — read and sync
- **Brew buttons** — one-click brew for all recipes
- **Action buttons** — pair, factory reset, descaling mode, eco mode, sync time, reset to production
- **Power switch** — turn machine on/off
- **Error binary sensors** — dosing unit dirty, low coffee, no water, drawer open, overheating, etc.

## Supported Machines

Compatible with machines using the BLE service UUID `c08b0100-6407-4a30-8aab-ccbbae8b7a4a`. Developed and tested on **Nescafé Gold Blend Barista**.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open the HACS repository.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ngoc-minh-do&repository=ha-nescafe-ble&category=integration)

Or manually:

1. Open HACS → **Integrations** → **⋮** → **Custom repositories**
2. Paste `https://github.com/ngoc-minh-do/ha-nescafe-ble` and select **Integration**
3. Search for **Nescafé BLE** and install
4. Restart HA

### Manual

```bash
git clone https://github.com/ngoc-minh-do/ha-nescafe-ble
cp -r custom_components/nescafe_ble /path/to/config/custom_components/
```

## Configuration

The integration is discovered automatically via Bluetooth. When HA detects a Barista machine nearby, a configuration notification appears. Alternatively, go to **Settings → Devices → Add Integration → Nescafé BLE**.

Options:
- **Polling interval** — how often to read machine data (default: 60s)

## BLE Pairing

Some characteristics (counters, parameter bits, HMI button commands) require BLE bonding. The integration calls `pair()` automatically before accessing protected data. Pairing only works when the HA Bluetooth adapter supports it:

- **ESP32 BLE proxy**: supported via the `pair()` command (ESPHome ≥2024.3.0 required)
- **Direct USB/Built-in BLE adapter**: supported

If pairing is unavailable, the integration falls back gracefully — unprotected data (status, coffee level, machine info) is still available.

## CLI Tool (`brewctl.py`)

A standalone CLI for controlling the machine outside of Home Assistant:

```bash
# Scan for machines
brewctl.py scan

# Read status
brewctl.py status AA:BB:CC:DD:EE:FF

# Brew a recipe
brewctl.py brew AA:BB:CC:DD:EE:FF espresso

# Toggle power
brewctl.py power AA:BB:CC:DD:EE:FF

# Read counters
brewctl.py counters AA:BB:CC:DD:EE:FF

# Pair
brewctl.py pair AA:BB:CC:DD:EE:FF

# Sync time
brewctl.py set-time AA:BB:CC:DD:EE:FF
```

## Example Card

A `dashboard.yaml` is included with an example card view using `stack-in-card`, `button-card`, and built-in button entities. It shows machine status with warnings (no water, rinse, low beans), quick rinse/power toggles, and a 3-column brew grid.

Requires these HACS frontend plugins:
- [stack-in-card](https://github.com/custom-cards/stack-in-card)
- [button-card](https://github.com/custom-cards/button-card)

Paste the contents of `dashboard.yaml` into an **Edit as YAML** dashboard view, or embed it as a card in your existing dashboard using `Manual` card type.

## Development

```bash
uv sync
make install     # Install deps + pre-commit
make lint        # ruff check
make format      # ruff format
make typecheck   # pyright
make test        # pytest
make check       # lint + format-check + test + typecheck
```

## Protocol

The machine exposes a BLE GATT service at `c08b0100-6407-4a30-8aab-ccbbae8b7a4a` with characteristics for status, counters, HMI button commands, recipes, and configuration. Full BLE UUID map is in `nescafe_client.py` and `brewctl.py`.

Decompiled Android SDK sources are in `nescafe-android/` and `nescafe-source/` for reference.

## License

MIT
