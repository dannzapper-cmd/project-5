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
- Support **learning loops** (MLflow, fine-tuning, continual learning, Flower, RL)
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

**Phase 4 — MLOps + Fine-tuning + Continual Learning**

| Delivered | Not Yet Implemented |
|-----------|---------------------|
| Phase 1–3: telemetry, ONNX edge AI, LangGraph agents, HITL, copilot | Sensor fusion |
| Synthetic dataset pipeline + data cards | Digital twin, ROS2 |
| v1 vs v2 candidate offline evaluation | Federated learning (Flower) |
| Optional MLflow (learning profile) + local artifact fallback | Full observability stack |
| Sliding-window drift detector + manual promotion workflow | |
| Dashboard MLOps panel (polling) | |

**Next phase:** [Phase 5 — Digital Twin + ROS2 Core](ROADMAP.md#phase-5-digital-twin--ros2-core)

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
- Fine-tuning
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
| MLOps and learning loops | MLflow, fine-tuning, Flower, RL (future phases) |
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
