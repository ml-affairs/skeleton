SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON_VERSION_FILE := .python-version
PYTHON_VERSION ?= $(shell test -f $(PYTHON_VERSION_FILE) && cat $(PYTHON_VERSION_FILE) || echo 3.12.10)
UV ?= $(shell if command -v uv >/dev/null 2>&1; then command -v uv; elif [ -x "$$HOME/.local/bin/uv" ]; then printf "%s\n" "$$HOME/.local/bin/uv"; else printf "uv\n"; fi)
UV_CACHE_DIR ?= .uv-cache
UV_RUN := UV_CACHE_DIR="$(UV_CACHE_DIR)" $(UV) run --python "$(PYTHON_VERSION)"
PYTEST_COV_ARGS := --cov=skeleton_replay --cov-report=term-missing --cov-report=xml --cov-fail-under=75
DEMO_PROJECT_ROOT ?= tests/fixtures/sample_project
DEMO_SCRIPT ?= $(DEMO_PROJECT_ROOT)/app.py
DEMO_OUT_DIR ?= tests/dev/.temp/skeleton-demo
PYTEST_BASETEMP ?= tests/dev/.temp/pytest

.PHONY: help check-uv setup sync install-hooks lint format format-check typecheck test test-cov check where demo demo-no-open clean commit-msg-example

help:
	@printf "Skeleton development targets\n"
	@printf "  make setup        Create .venv and sync development dependencies\n"
	@printf "  make sync         Sync project and development dependencies\n"
	@printf "  make install-hooks Install pre-commit and commit-msg hooks\n"
	@printf "  make lint         Run Ruff checks\n"
	@printf "  make format       Format Python files with Ruff\n"
	@printf "  make typecheck    Run mypy\n"
	@printf "  make test         Run pytest\n"
	@printf "  make test-cov     Run pytest with coverage gate\n"
	@printf "  make check        Run lint, format-check, typecheck, and tests\n"
	@printf "  make where        Print local artifact locations\n"
	@printf "  make demo         Run the sample project, write stable artifacts, and open report.html\n"
	@printf "  make demo-no-open Run the sample project without opening report.html\n"
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

test-cov: check-uv
	@$(UV_RUN) python -m pytest $(PYTEST_COV_ARGS)

check: lint format-check typecheck test-cov
	@printf "All checks passed.\n"

where:
	@printf "Skeleton local artifact locations\n"
	@printf "  stable demo report    %s/report.html\n" "$(DEMO_OUT_DIR)"
	@printf "  stable demo artifacts %s/\n" "$(DEMO_OUT_DIR)"
	@printf "  pytest temp root      %s/\n" "$(PYTEST_BASETEMP)"
	@printf "  package CLI default   %s\n" "$$HOME/.skeleton/<application-name>/"
	@printf "\n"
	@printf "Common commands\n"
	@printf "  make demo-no-open     regenerate %s/report.html\n" "$(DEMO_OUT_DIR)"
	@printf "  make demo             regenerate and open %s/report.html\n" "$(DEMO_OUT_DIR)"
	@printf "  make test             run tests with temp files under %s/\n" "$(PYTEST_BASETEMP)"

demo: check-uv
	@mkdir -p "$(DEMO_OUT_DIR)"
	@SKELETON_OUT_DIR="$(DEMO_OUT_DIR)" $(UV_RUN) python -m skeleton_replay run --project-root "$(DEMO_PROJECT_ROOT)" "$(DEMO_SCRIPT)"

demo-no-open: check-uv
	@mkdir -p "$(DEMO_OUT_DIR)"
	@SKELETON_OUT_DIR="$(DEMO_OUT_DIR)" $(UV_RUN) python -m skeleton_replay run --no-open --project-root "$(DEMO_PROJECT_ROOT)" "$(DEMO_SCRIPT)"

commit-msg-example:
	@printf "Valid semantic commit message examples:\n"
	@printf "  feat(cli): add replay command\n"
	@printf "  fix(runtime): ignore private calls\n"
	@printf "  docs!: rewrite package overview\n"

clean:
	@rm -rf .mypy_cache .pytest_cache .ruff_cache build dist *.egg-info tests/dev/.temp/skeleton-demo tests/dev/.temp/pytest
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
