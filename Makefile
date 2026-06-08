.PHONY: help install test lint dev-check api compose-config compose-core clean \
	telemetry-up telemetry-down telemetry-logs replay-generate \
	replay-normal replay-fatigue replay-dropout replay-spike replay-multi api-status \
	models-generate benchmark-inference edge-ai-up edge-ai-logs model-status \
	test-phase-regression evidence-phase3 mlops-pipeline verify-phase4 compose-learning \
	compose-ros2 twin-status ros2-logs \
	compose-nav-slam nav-slam-up nav-slam-down nav-slam-logs nav-slam-ps nav-slam-status \
	nav-slam-map-demo nav-slam-goal-demo nav-slam-blocked-demo nav-slam-nodes nav-slam-topics \
	learning-install learning-fl-run learning-fl-smoke learning-fl-report fl-status verify-phase6a

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

compose-ros2: ## Validate Docker Compose ros2 profile configuration
	docker compose --profile core --profile ros2 config

twin-status: ## Fetch digital twin service status
	curl -s http://localhost:8000/api/v1/twin/status | python3 -m json.tool

ros2-up: ## Start core + ROS2 bridge profiles
	docker compose --profile core --profile ros2 up --build

ros2-logs: ## Tail ROS2 bridge logs
	docker compose --profile ros2 logs -f ros2_bridge

# --- Phase 5.5 Nav2 + SLAM MiniLab (isolated ros2-nav-slam profile) ---
NAVSLAM := docker compose --profile ros2-nav-slam
NAVSLAM_SVC := ros2_nav_slam
NAVSLAM_EXEC := $(NAVSLAM) exec $(NAVSLAM_SVC) bash -lc 'source /opt/ros/humble/setup.bash && source /ros2_ws/install/setup.bash &&

compose-nav-slam: ## Validate Docker Compose ros2-nav-slam profile configuration
	docker compose --profile ros2-nav-slam config

nav-slam-up: ## Start Nav2 + SLAM MiniLab (ros2-nav-slam profile)
	$(NAVSLAM) up --build -d

nav-slam-down: ## Stop Nav2 + SLAM MiniLab profile
	$(NAVSLAM) down

nav-slam-logs: ## Tail MiniLab logs (last 200 lines)
	$(NAVSLAM) logs --tail=200 -f $(NAVSLAM_SVC)

nav-slam-ps: ## Show MiniLab service status
	$(NAVSLAM) ps

nav-slam-nodes: ## List ROS2 nodes in the MiniLab
	$(NAVSLAM_EXEC) ros2 node list'

nav-slam-topics: ## List ROS2 topics in the MiniLab
	$(NAVSLAM_EXEC) ros2 topic list'

nav-slam-status: ## Fetch Nav2/SLAM MiniLab status from local API
	curl -s http://localhost:8000/api/v1/nav-slam/status | python3 -m json.tool

nav-slam-map-demo: ## Start SLAM mapping demo (synthetic scan/odom/TF -> /map)
	$(NAVSLAM_EXEC) ros2 service call /axon/nav_slam/start_mapping std_srvs/srv/Trigger {}'

nav-slam-goal-demo: ## Send a reachable navigation goal (open floor)
	$(NAVSLAM_EXEC) ros2 service call /axon/nav_slam/send_goal axon_nav_slam_interfaces/srv/SendNavGoal "{x: 5.0, y: 1.0, theta_deg: 0.0, demo: nav_goal_demo, trace_id: qa-goal}"'

nav-slam-blocked-demo: ## Send a goal inside an obstacle (expect blocked state)
	$(NAVSLAM_EXEC) ros2 service call /axon/nav_slam/send_goal axon_nav_slam_interfaces/srv/SendNavGoal "{x: 4.2, y: 1.3, theta_deg: 0.0, demo: blocked_goal_demo, trace_id: qa-blocked}"'

# --- Phase 6A Federated Learning (on-demand learning profile) ---
learning-install: ## Install Phase 6A FL deps (Flower + CPU torch + MLflow), isolated from core
	$(PIP) install torch --index-url https://download.pytorch.org/whl/cpu
	$(PIP) install -r requirements-learning.txt

learning-fl-run: ## Run the Flower FedAvg federated learning simulation (default 3 clients)
	$(PYTHON) scripts/run_federated_learning.py --num-clients $${FL_NUM_CLIENTS:-3} --num-rounds $${FL_NUM_ROUNDS:-5} --local-epochs $${FL_LOCAL_EPOCHS:-3} --seed $${FL_SEED:-42}

learning-fl-smoke: ## Run a tiny CI-friendly federated simulation (2 clients, 1 round)
	$(PYTHON) scripts/run_federated_learning.py --smoke

learning-fl-report: ## Print the latest federated learning report
	@test -f artifacts/learning/federated/federated_report.json \
		&& $(PYTHON) -m json.tool artifacts/learning/federated/federated_report.json \
		|| echo "No report yet. Run 'make learning-fl-run' first."

fl-status: ## Fetch federated learning status from the local API
	curl -s http://localhost:8000/api/learning/federated/status | python3 -m json.tool

verify-phase6a: ## Run the Phase 6A verification script (lint + FL tests + smoke + compose)
	bash scripts/verify_phase6a.sh
