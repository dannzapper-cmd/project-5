.PHONY: help install test lint dev-check api compose-config compose-core clean

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
UVICORN := $(VENV)/bin/uvicorn

help: ## Show available commands
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install package with dev dependencies
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

test: ## Run Phase 0 unit tests (no external services)
	$(PYTEST) tests/

lint: ## Run ruff linter
	$(RUFF) check apps scripts tests

dev-check: ## Run lightweight dev validation script
	$(PYTHON) scripts/dev_check.py

api: ## Start FastAPI dev server (Phase 0 health endpoint only)
	$(UVICORN) apps.api.main:app --reload --host 0.0.0.0 --port 8000

compose-config: ## Validate Docker Compose core profile configuration
	docker compose --profile core config

compose-core: ## Start core profile skeleton services (Phase 0 placeholders)
	docker compose --profile core up --build

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
