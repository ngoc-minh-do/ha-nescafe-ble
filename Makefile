.PHONY: install lint format format-check typecheck test check fix clean precommit release

install:
	uv sync
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

lint:
	uv run ruff check

format:
	uv run ruff format

format-check:
	uv run ruff format --check

typecheck:
	uv run pyright

test:
	uv run pytest; EXIT_CODE=$$?; if [ $$EXIT_CODE -eq 5 ]; then exit 0; else exit $$EXIT_CODE; fi

check: lint format-check typecheck test

fix:
	uv run ruff check --fix
	uv run ruff format

precommit:
	uv run pre-commit run --all-files

release:
	uv run cz bump $(if $(VERSION),$(VERSION),) --no-verify
	git push --follow-tags

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .ruff_cache .pyright_cache
