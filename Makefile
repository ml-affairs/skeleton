SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON_VERSION_FILE := .python-version
PYTHON_VERSION ?= $(shell test -f $(PYTHON_VERSION_FILE) && cat $(PYTHON_VERSION_FILE) || echo 3.12.10)
UV ?= $(shell if command -v uv >/dev/null 2>&1; then command -v uv; elif [ -x "$$HOME/.local/bin/uv" ]; then printf "%s\n" "$$HOME/.local/bin/uv"; else printf "uv\n"; fi)
UV_CACHE_DIR ?= .uv-cache
UV_RUN := UV_CACHE_DIR="$(UV_CACHE_DIR)" $(UV) run --python "$(PYTHON_VERSION)"

.PHONY: help check-uv setup sync install-hooks lint format format-check typecheck test check clean commit-msg-example

help:
	@printf "Skeleton development targets\n"
	@printf "  make setup        Create .venv and sync development dependencies\n"
	@printf "  make sync         Sync project and development dependencies\n"
	@printf "  make install-hooks Install pre-commit and commit-msg hooks\n"
	@printf "  make lint         Run Ruff checks\n"
	@printf "  make format       Format Python files with Ruff\n"
	@printf "  make typecheck    Run mypy\n"
	@printf "  make test         Run pytest\n"
	@printf "  make check        Run lint, format-check, typecheck, and tests\n"
	@printf "  make clean        Remove local caches and build artifacts\n"

check-uv:
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "uv is required but was not found."; \
		echo "Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 127; \
	}

setup: check-uv
	@UV_CACHE_DIR="$(UV_CACHE_DIR)" $(UV) venv --clear --python "$(PYTHON_VERSION)" .venv
	@UV_CACHE_DIR="$(UV_CACHE_DIR)" $(UV) sync --all-groups --python "$(PYTHON_VERSION)"
	@$(MAKE) install-hooks

sync: check-uv
	@UV_CACHE_DIR="$(UV_CACHE_DIR)" $(UV) sync --all-groups --python "$(PYTHON_VERSION)"

install-hooks: check-uv
	@$(UV_RUN) python -m pre_commit install --hook-type pre-commit --hook-type commit-msg
	@printf "Pre-commit and commit-msg hooks installed.\n"

lint: check-uv
	@$(UV_RUN) ruff check .

format: check-uv
	@$(UV_RUN) ruff format .

format-check: check-uv
	@$(UV_RUN) ruff format --check .

typecheck: check-uv
	@$(UV_RUN) mypy

test: check-uv
	@$(UV_RUN) python -m pytest

check: lint format-check typecheck test
	@printf "All checks passed.\n"

commit-msg-example:
	@printf "Valid semantic commit message examples:\n"
	@printf "  feat(cli): add replay command\n"
	@printf "  fix(runtime): ignore private calls\n"
	@printf "  docs!: rewrite package overview\n"

clean:
	@rm -rf .mypy_cache .pytest_cache .ruff_cache build dist *.egg-info
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
