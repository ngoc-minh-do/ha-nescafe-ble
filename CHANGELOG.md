## v0.1.3 (2026-08-02)

### Feat

- add commitizen hook for commit message validation

### Refactor

- remove coffee level sensor from all files
- remove bleak, bleak-retry-connector, and pycryptodome from project dependencies (provided by HA)

### Docs

- update README: remove coffee level, update poll interval, document brew-wake and all CLI commands

### Ci

- add CI workflow to validate manifest version matches git tag

## v0.1.2 (2026-07-28)

### Feat

- add from_bytes(), wake_and_brew_hmi(), and brew-wake CLI to brewctl.py
- add wake-and-brew HMI flow with real-time status updates
- add busy flag to prevent coordinator poll / button press conflicts

### Changes

- change default scan interval from 60s to 86400s (1 day)
- downgrade get_info errors from exception→warning, log button presses
- rename Nescafe Barista to Nescafe Gold Blend Barista

### Docs

- add example card section to README referencing dashboard.yaml
- add example dashboard

## v0.1.1 (2026-07-27)

### Feat

- add 2s cooldown after any button press
- add icons for sensors and buttons
- add debug logging to all BLE interactions

### Fix

- align recipe button names with phone app display names
- power_on_off (action button) should not be EntityCategory.CONFIG
- convert power switch to button entity
- fix ruff lint issues: BLE001 and S110

## v0.1.0 (2026-07-27)

### Feat

- expose parameter_bits_paired as Active Modes sensor with human-readable flags
- add get_parameter_bits_paired() read, add reset_to_production_mode() (bit 3)

### Fix

- add missing replenishModeOn and rfu peripheral flags (bits 9-10)
- use bleak-retry-connector's establish_connection for reliable BLE connections

### Refactor

- centralize DeviceInfo in device.py, use BLE discovery name as model, fix docstring
