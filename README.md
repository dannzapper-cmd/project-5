# AXON - Bio-Robotics Edge Command System

**Perceive. Decide. Learn. Operate.**

AXON is a modular Edge AI, IoT, robotics software, and biomedical-inspired synthetic monitoring system for simulated rehabilitation robot operations.

---

## What AXON Is

A reproducible intelligent systems project that will:

- Ingest **synthetic telemetry** (EMG, ECG-like, IMU, SpO2-proxy, robot state, environment)
- Run **edge-like inference** with ONNX Runtime
- **Fuse sensors** into operational state with confidence scoring
- **Coordinate agents** via LangGraph with LangChain tools/RAG
- Support **learning loops** (MLflow, synthetic retraining / candidate refresh loop, Flower, RL)
- **Visualize operations** through a live dashboard and digital twin
- Collect **evidence** for every major capability

**Expanded name:** Autonomous eXecution and Operations Network  
**Fixed scenario:** Simulated Rehab Robot Ops

## What AXON Is Not

- Not a chatbot
- Not a static dashboard
- Not a medical device
- Not a diagnostic system
- Not based on real patient data
- Not dependent on expensive always-on infrastructure
- Not a robotics hardware project blocked by physical devices

---

## Future High-Level Architecture

```
Synthetic Sensors / IoT Nodes
        │
        ▼
   MQTT / Mosquitto
        │
        ▼
FastAPI async gateway + Pydantic event schemas
        │
        ▼
Redis Streams buffer + replay mode
        │
        ├──────────────────┐
        ▼                  ▼
ONNX Runtime          Sensor Fusion
 edge inference            │
        │                  │
        └────────┬─────────┘
                 ▼
        LangGraph Agent Layer
                 │
                 ▼
   LangChain tools / RAG / retrievers
                 │
                 ▼
        WebSocket broadcast
                 │
        ┌────────┴────────┐
        ▼                 ▼
  Dashboard +      Evidence Center
  Digital Twin
        │
        ├─ MLflow / Observability / Learning Loops
        ├─ ROS2 thin adapter
        └─ Advanced ROS2 Nav2 + SLAM MiniLab profile
```

See [docs/architecture/](docs/architecture/) for Mermaid diagrams and profile details.

---

## Current Phase

**Phase 9 — QA, Repair, and Hardening (in progress on `feat/phase-9-pass1-credibility-hardening`)**

| Completed (merged) | Current work (Phase 9) | Not yet |
|--------------------|------------------------|---------|
| Phases 1–8: telemetry, edge AI, agents, HITL, MLOps synthetic retraining loop, digital twin, ROS2, Nav2 + SLAM MiniLab, FL/RL, observability/reliability, integrated mission control | Credibility repairs, evidence integrity, reproducibility, phase/version alignment, lightweight CI expansion | Phase 10 packaging, demo video, portfolio release |

**Phase 8 (merged):** Mission API (`/mission/*`), deterministic scenario runner (seed 42),
Evidence Center index, dashboard Mission Control section. See
[docs/phase8_mission_control.md](docs/phase8_mission_control.md).

**Phase 4 MLOps note:** AXON includes a synthetic retraining / candidate refresh loop for
small classical models. It is not fine-tuning of a pretrained neural network.

**Next after Phase 9:** [Phase 10 — Portfolio Packaging](ROADMAP.md) (not started).

> **Synthetic data only. No real patient data. No medical claims. Human review required
> for high-risk actions.**

---

## Phase 5.5 — Nav2 + SLAM MiniLab Quickstart

Headless, isolated, reproducible. **No physical robot. No medical claims.**
`core` is unaffected and does not depend on this profile.

```bash
make install && make test && make lint
make compose-config        # core profile valid
make compose-nav-slam      # ros2-nav-slam profile valid

# Core stays independent
docker compose --profile core up --build -d

# Start the MiniLab (heavy image: Nav2 + SLAM Toolbox on ros:humble-ros-base)
docker compose --profile ros2-nav-slam up --build -d
make nav-slam-ps
make nav-slam-nodes
make nav-slam-topics

# Synthetic data rates (B3): defaults target /scan 12 Hz, /odom 25 Hz
# Hard gates remain /scan >= 10 Hz, /odom >= 20 Hz.
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic hz /scan
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic hz /odom
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 run tf2_tools view_frames  # map->odom->base_link

# Demos
make nav-slam-map-demo      # SLAM mapping from synthetic scan/odom/TF
make nav-slam-goal-demo     # reachable goal -> planning -> navigating -> reached
make nav-slam-blocked-demo  # goal inside obstacle -> blocked (honest)
make nav-slam-status        # AXON-side status; dashboard panel http://localhost:3000
make nav-slam-down
```

**What Phase 5.5 does not do:** medical diagnosis, real patient data, hardware,
cloud deployment, Gazebo/RViz, federated learning, RL, Kubernetes.

Evidence checklist: [docs/evidence/phase-5-5-nav2-slam-minilab.md](docs/evidence/phase-5-5-nav2-slam-minilab.md)
· ADRs: [ADR-009](docs/adr/ADR-009-nav2-slam-minilab-scope.md), [ADR-010](docs/adr/ADR-010-headless-minisim-no-gazebo-rviz.md)

---

## Phase 5 — Digital Twin + ROS2 Quickstart

```bash
make install
make test
make models-generate
docker compose --profile core up --build -d

# Dashboard digital twin: http://localhost:3000
curl -s http://localhost:8000/api/v1/twin/state | python3 -m json.tool
curl -s http://localhost:8000/health | python3 -m json.tool

# Live generators (QA-LIVE-1)
# Twin updates via /ws/v1/twin within ~200ms at 5 Hz

# Replay scenarios (QA-LIVE-3)
make replay-normal
make replay-fatigue
make replay-dropout

# Staleness demo (QA-LIVE-2): stop sensor-generators, wait for stale/dropout TTLs
docker compose --profile core stop sensor-generators

# Safe commands
curl -X POST http://localhost:8000/api/v1/twin/command \
  -H 'Content-Type: application/json' \
  -d '{"schema_version":"v1","command":"pause","requested_by":"qa"}'

# ROS2 profile (requires core API running)
docker compose --profile core --profile ros2 up --build -d
docker compose --profile ros2 exec ros2_bridge ros2 topic echo /axon/twin/state
```

**What Phase 5 does not do:** medical diagnosis, real patient data, Nav2, SLAM, navigation stack, heavy simulation.

Evidence checklist: [docs/evidence/phase-5-digital-twin-ros2.md](docs/evidence/phase-5-digital-twin-ros2.md)

---

## Phase 4 — MLOps Quickstart

```bash
make install
make models-generate
make mlops-pipeline      # smoke dataset + train/eval
make verify-phase4       # full Phase 4 verification

# Optional MLflow UI (learning profile)
docker compose --profile learning up -d mlflow
# http://localhost:5001
AXON_MLOPS_BACKEND=mlflow make mlops-pipeline
```

API: `GET /api/v1/mlops/status` · Dashboard MLOps panel polls every 10s.

---

## Phase 3 — Agents + Safety Quickstart

```bash
make install
make models-generate
docker compose --profile core up --build

# Verify agents
curl http://localhost:8000/api/v1/agents/traces
curl http://localhost:8000/api/v1/decisions/current
curl http://localhost:8000/api/v1/safety/status
redis-cli XLEN axon:v1:stream:agent_traces

# Failure injection demo
curl -X POST http://localhost:8000/api/v1/failure-injection/model_low_confidence
curl -X POST http://localhost:8000/api/v1/failure-injection/reset

# Evidence + regression
make evidence-phase3
make test-phase-regression
```

Dashboard: http://localhost:3000 — telemetry, model scores, agent traces, HITL, MLOps.

### Core Mode (default — no API keys)

Mock LLM is default. Core profile runs without `OPENAI_API_KEY` or provider packages.

### Real LLM Mode (optional portfolio demo)

```bash
export AXON_LLM_MODE=real
export AXON_LLM_PROVIDER=openai
export AXON_LLM_MODEL=gpt-4o-mini
export OPENAI_API_KEY=your-key-here
docker compose --profile core --profile llm up --build
```

---

## Phase 2 — Edge AI Core Quickstart

```bash
# Step 1: Generate ONNX models (required before Docker build)
make models-generate

# Step 2: Start Phase 2 core stack
docker compose --profile core up --build
# or: make edge-ai-up

# Verify
curl http://localhost:8000/telemetry/status
curl http://localhost:8000/model-scores/status
redis-cli XLEN axon:v1:stream:model_scores

# Benchmark (local, no Docker)
make benchmark-inference
```

Dashboard: http://localhost:3000 — live telemetry + model score panels.

---

## Mandatory Roadmap Technologies

- Edge AI
- IoT and real-time telemetry
- MQTT / Eclipse Mosquitto
- Redis Streams
- FastAPI + WebSockets
- Pydantic event schemas
- ONNX Runtime edge inference
- Sensor fusion
- Deep learning with small models
- Synthetic retraining / candidate refresh loop (classical models — not neural fine-tuning)
- TinyML / tiny deep learning path
- MLflow for MLOps
- Continual learning
- Federated learning with Flower
- RL micro-module with Gymnasium / Stable-Baselines3
- LangGraph (main agent orchestration runtime)
- LangChain (tools, RAG, retrievers, research/model-call layer)
- Human-in-the-loop safety
- Safety boundaries
- Failure injection
- Replay mode
- OpenTelemetry / metrics / logs
- Docker Compose profiles
- Evidence Center
- Digital twin
- ROS2 thin adapter
- Full ROS2 Nav2 + SLAM MiniLab (mandatory advanced phase)
- Cost and hardware report
- Optional hardware: ESP32, Raspberry Pi, Jetson Nano, Edge Impulse / TFLite Micro

---

## Docker Compose Profiles

Profiles prevent all systems from running at once and enable staged development.

| Profile | Purpose |
|---------|---------|
| `core` | API, dashboard, Redis, Mosquitto, sensor-generators, edge-inference |
| `obs` | Prometheus, Grafana (Phase 7+) |
| `learning` | MLflow (Phase 4+) |
| `ros2` | ROS2 thin adapter (Phase 5+) |
| `ros2-nav-slam` | Nav2 + SLAM MiniLab (Phase 5.5, mandatory) |
| `sim` | Sensor simulation orchestrator (Phase 1+) |
| `llm` | Optional LLM copilot (Phase 3+, not always-on) |
| `full` | Union of all profiles for late integration demos |

```bash
# Validate core profile
make compose-config

# Start Phase 2 edge AI stack
make models-generate
make edge-ai-up
# or: make compose-core
```

Details: [docs/architecture/profiles.md](docs/architecture/profiles.md)

---

## Safety and Biomedical Boundary

AXON uses **synthetic biomedical-inspired signals only**.

- No real patient data
- No diagnosis or treatment advice
- No clinical or medical-device claims
- Software engineering simulation for portfolio demonstration

Policies: [docs/safety/](docs/safety/)

---

## Why This Is Senior-Leaning

| Practice | AXON Implementation |
|----------|---------------------|
| Event-driven architecture | MQTT → API → Redis → services → WebSocket |
| Data contracts | Pydantic v2 schemas + topic taxonomy |
| Safety boundaries | Biomedical policy + HITL policy |
| Human-in-the-loop | `requires_human_confirmation` in decision events |
| Evidence Center | Phase-gated checklist with reproducible proof |
| MLOps and learning loops | MLflow, synthetic retraining / candidate refresh loop, Flower, RL |
| Observability | OpenTelemetry, Prometheus, Grafana (Phase 7) |
| Robotics integration | ROS2 thin adapter + mandatory Nav2 MiniLab |
| Replay and failure injection | MQTT replay publish + Redis buffer (Phase 1) |
| Modular profiles | Documented trade-offs in ADRs and cost docs |

---

## Claims We Avoid

- Medical-grade monitoring
- Diagnosis of arrhythmia, fatigue, oxygen problems, or clinical conditions
- Production-ready medical device
- Real hospital/clinic deployment
- Autonomous clinical decision-maker
- Enterprise healthcare compliance claims

---

## Repository Structure

```
apps/api/                      FastAPI gateway + MQTT ingest + WebSockets
apps/dashboard/                Live Phase 2 dashboard (telemetry + model scores)
services/edge-inference/       ONNX Runtime edge inference service
models/                        ONNX artifacts + metadata (generated)
services/sensor-generators/    Synthetic MQTT publishers
replay/                        JSONL scenarios + replay_publish.py
docs/                          Architecture, ADRs, safety, evidence, schemas
infra/                         Mosquitto, Prometheus, Grafana configs
tests/                         Schema, generator, routing, replay tests
scripts/                       Dev validation scripts
```

---

## Python Packaging

Dependencies are managed in **`pyproject.toml`** (not `requirements.txt`).

`pyproject.toml` provides a modern single place for project metadata, dependencies, optional dependency groups, test configuration, and lint configuration — keeping Phase 0 installs lightweight while allowing phase-specific extras later.

---

## Commands

### Setup

```bash
git pull
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,edge-ai]"
make test
make dev-check
```

### Phase 1 — Telemetry Spine

```bash
# Validate Compose config
docker compose --profile core config
# or: make compose-config

# Start full spine (Mosquitto, Redis, API, generators, dashboard)
docker compose --profile core up --build
# or: make telemetry-up

# URLs (browser on host machine)
# Dashboard:  http://localhost:3000
# API health: http://localhost:8000/health
# Telemetry:  http://localhost:8000/telemetry/status

make api-status   # pretty-print telemetry status JSON
make telemetry-logs
make telemetry-down
```

### Replay

```bash
make replay-generate    # regenerate JSONL scenario files
make replay-normal      # publish normal_session to MQTT
make replay-dropout     # publish sensor_dropout scenario
```

### Phase 1 Evidence (collect after demo)

| Artifact | How to capture |
|----------|----------------|
| Dashboard live telemetry | Screenshot at http://localhost:3000 |
| Generator logs | `docker compose logs sensor-generators` |
| Telemetry status | `curl http://localhost:8000/telemetry/status` |
| Redis stream proof | `redis-cli XLEN axon:v1:stream:sensors:emg` |
| MQTT proof | `mosquitto_sub -t 'axon/v1/sensors/#' -v` |

See [docs/evidence/evidence-checklist.md](docs/evidence/evidence-checklist.md).

### Future Phases

```bash
# Full portfolio demo (Phase 9 — not yet implemented)
# docker compose --profile full up
```

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [ROADMAP.md](ROADMAP.md) | Phased delivery plan |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | AI agent and contributor context |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution rules |
| [docs/architecture/](docs/architecture/) | System diagrams |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [docs/evidence/](docs/evidence/) | Evidence Center |
| [docs/safety/](docs/safety/) | Safety policies |
| [docs/schemas/](docs/schemas/) | Event contracts and topic taxonomy |

---

## License

MIT (see project metadata in `pyproject.toml`).

---

*AXON — Simulated Rehab Robot Ops. Synthetic signals only. Not for clinical use.*
