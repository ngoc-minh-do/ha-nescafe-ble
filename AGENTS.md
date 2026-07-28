# AGENTS.md — ha-nescafe-ble

Home Assistant custom integration for Nescafé Gold Blend Barista BLE machines. Domain: `nescafe_ble`.

## Quick commands

```sh
make install     # uv sync + pre-commit install
make lint        # ruff check
make format      # ruff format
make format-check# ruff format --check
make typecheck   # pyright
make test        # pytest (passes even with zero tests, exit 5→0)
make check       # lint → format-check → test → typecheck (full gate)
make fix         # ruff check --fix + ruff format
make clean       # rm __pycache__, .ruff_cache, .pyright_cache
```

## Key facts

- **Default branch**: `master` (not `main`). CI (HACS Action, hassfest) triggers on push/PR to `master`.
- **Python**: 3.14+, managed with `uv`.
- **All integration source** lives under `custom_components/nescafe_ble/`. `src/` is empty.
- CLI tool: `brewctl.py` — standalone BLE controller outside HA.
- Decompiled Android SDK reference in `nescafe-android/` and `nescafe-source/`.

## Code conventions

- `pyrightconfig.json` suppresses `reportIncompatibleVariableOverride` and `reportTypedDictNotRequiredAccess`.
- Pre-commit runs `ruff check --fix`, `ruff format`, and `pyright` on commit.
- Button cooldown: `BUTTON_COOLDOWN = 2.0` in `button.py` — all commands have a global rate limit.
- `TYPE_CHECKING` guard used in `__init__.py` to import types, consistent with HA patterns.

## HMI button commands (C08B protocol)

- **Service**: `c08b0100-6407-4a30-8aab-ccbbae8b7a4a`
- **Write char**: `C08B0107` — 2-byte unencrypted button codes
- Button codes in `RECIPE_TO_BUTTON_BYTE` (defined in `nescafe_client.py`).
- Brew actions use `wake_and_brew_hmi()`: subscribes to status notifications on `C08B0104`, sends power toggle (0x00 0x01) if sleeping, waits for PRE_HEAT → READY state transitions, then sends the brew button code.

## Test gaps

- `tests/` has only `__init__.py`. No real tests exist yet.
