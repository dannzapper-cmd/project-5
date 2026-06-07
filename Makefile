.PHONY: help install test lint dev-check api compose-config compose-core clean \
	telemetry-up telemetry-down telemetry-logs replay-generate \
	replay-normal replay-fatigue replay-dropout replay-spike replay-multi api-status \
	models-generate benchmark-inference edge-ai-up edge-ai-logs model-status \
	test-phase-regression evidence-phase3 mlops-pipeline verify-phase4 compose-learning

SYSTEM_PYTHON ?= python3.12
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
UVICORN := $(VENV)/bin/uvicorn
COMPOSE := docker compose --profile core

help: ## Show available commands
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install package with dev, edge-ai, agents, and mlops dependencies
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,edge-ai,agents,mlops]"

test: ## Run unit tests (no Docker/MQTT/Redis required)
	$(PYTEST) tests/

lint: ## Run ruff linter
	$(RUFF) check apps scripts tests services/sensor-generators replay

dev-check: ## Run lightweight dev validation script
	$(PYTHON) scripts/dev_check.py

api: ## Start FastAPI dev server locally
	$(UVICORN) apps.api.main:app --reload --host 0.0.0.0 --port 8000

compose-config: ## Validate Docker Compose core profile configuration
	docker compose --profile core config

compose-core: ## Start core profile (Phase 2 edge AI stack)
	$(COMPOSE) up --build

models-generate: ## Generate Phase 2 ONNX model artifacts
	$(PYTHON) scripts/generate_phase2_models.py

benchmark-inference: ## Run ONNX inference benchmark and write evidence report
	$(PYTHON) scripts/benchmark_inference.py

edge-ai-up: ## Start Phase 2 core stack (requires models-generate first)
	@test -f models/onnx/emg_anomaly_v0.onnx || \
		(echo "ERROR: Run 'make models-generate' first." && exit 1)
	$(COMPOSE) up --build

edge-ai-logs: ## Tail logs for edge inference and API
	$(COMPOSE) logs -f edge-inference api

model-status: ## Fetch model score status from local API
	curl -s http://localhost:8000/model-scores/status | python3 -m json.tool

test-phase-regression: ## Run Phase 1+2+3 regression test gate
	bash scripts/test_phase_regression.sh

evidence-phase3: ## Generate Phase 3 evidence artifacts (graph, trace, benchmarks)
	$(PYTHON) scripts/generate_phase3_evidence.py

telemetry-up: ## Start Phase 2 core stack in background
	$(COMPOSE) up --build -d

telemetry-down: ## Stop Phase 1 core stack
	$(COMPOSE) down

telemetry-logs: ## Tail logs for core stack
	$(COMPOSE) logs -f api sensor-generators mosquitto redis

replay-generate: ## Regenerate replay scenario JSONL files
	$(PYTHON) replay/generate_scenarios.py

replay-normal: ## Replay normal_session scenario to MQTT
	$(PYTHON) replay/replay_publish.py --file replay/scenarios/normal_session.jsonl --speed 0.5

replay-fatigue: ## Replay fatigue_event scenario
	$(PYTHON) replay/replay_publish.py --file replay/scenarios/fatigue_event.jsonl --speed 0.5

replay-dropout: ## Replay sensor_dropout scenario
	$(PYTHON) replay/replay_publish.py --file replay/scenarios/sensor_dropout.jsonl --speed 0.5

replay-spike: ## Replay movement_spike scenario
	$(PYTHON) replay/replay_publish.py --file replay/scenarios/movement_spike.jsonl --speed 0.5

replay-multi: ## Replay multi_anomaly scenario
	$(PYTHON) replay/replay_publish.py --file replay/scenarios/multi_anomaly.jsonl --speed 0.5

api-status: ## Fetch telemetry status from local API
	curl -s http://localhost:8000/telemetry/status | python3 -m json.tool

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

mlops-pipeline: ## Run Phase 4 MLOps pipeline (smoke mode)
	AXON_MLOPS_SMOKE=true $(PYTHON) scripts/run_mlops_pipeline.py --smoke

verify-phase4: ## Run Phase 4 verification script
	bash scripts/verify_phase4.sh

compose-learning: ## Validate Docker Compose learning profile
	docker compose --profile learning config
