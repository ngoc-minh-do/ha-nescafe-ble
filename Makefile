.PHONY: install lint format format-check typecheck test check fix clean

install:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check

format:
	uv run ruff format

format-check:
	uv run ruff format --check

typecheck:
	uv run pyright

test:
	uv run pytest

check: lint format-check test typecheck

fix:
	uv run ruff check --fix
	uv run ruff format

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .ruff_cache .pyright_cache
