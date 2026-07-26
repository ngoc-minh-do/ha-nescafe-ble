# Contributing

Thanks for your interest in contributing to Nescafé BLE!

## Development Setup

```bash
git clone https://github.com/ngoc-minh-do/ha-nescafe-ble.git
cd ha-nescafe-ble
uv sync
```

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

## Code Style

- Format with [Ruff](https://docs.astral.sh/ruff/)
- Type-check with [Pyright](https://github.com/microsoft/pyright)
- Run `make check` to run all checks

## Testing

Test the integration locally by symlinking or copying `custom_components/nescafe_ble/` into your Home Assistant config's `custom_components/` directory, then restart Home Assistant.

## Pull Requests

1. Fork the repo and create a branch from `main`
2. Make your changes and ensure `make check` passes
3. Open a PR with a clear description of the change
