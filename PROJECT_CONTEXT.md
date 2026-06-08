# AXON Project Context

Compact reference for AI agents and human contributors.

## Project Intent

**AXON** (Autonomous eXecution and Operations Network) is a portfolio-grade intelligent systems project for **Simulated Rehab Robot Ops**. It will ingest synthetic telemetry, run edge-like inference, fuse sensors, coordinate agents, support learning loops, and visualize operations through a dashboard and digital twin.

**Tagline:** Perceive. Decide. Learn. Operate.

## Fixed Scenario

Simulated rehabilitation robot, exoskeleton, or robotic arm operations with synthetic biomedical-inspired signals (EMG, ECG-like, IMU, SpO2-proxy) and robot-state telemetry.

## Non-Negotiables

1. Synthetic biomedical-inspired signals only — no real patient data
2. No medical diagnosis, treatment advice, or clinical claims
3. LangGraph = main agent orchestration; LangChain = tools/RAG/retrievers layer
4. Redis Streams (not Kafka as core) for buffering/replay
5. ONNX Runtime for edge inference path
6. Docker Compose profiles — not everything always-on
7. Phase 5.5 Nav2 + SLAM MiniLab is **mandatory advanced**, not optional
8. Evidence-driven — every major feature produces visible proof
9. **Do not collapse AXON into a chatbot, a single dashboard, or a generic CRUD application.**
10. **Do not remove mandatory roadmap phases unless the human owner explicitly changes the project direction.**
11. **Do not write documentation that claims Phase 1+ functionality is already working during Phase 0.**

## Architecture Principles

- Event-driven with Pydantic contracts
- Validate before inference
- Trace ID propagation end-to-end
- Human-in-the-loop for high-risk/low-confidence actions
- Profile-based modular activation
- Local-first; cloud/VM on demand
- Thin ROS2 adapter; heavy Nav2 lab isolated in `ros2-nav-slam` profile

## Current Phase

**Phase 7 — Observability + Reliability (lightweight local layer)**

Delivered on branch `feat/phase-7-observability-reliability`:

- **Reliability:** `/health/live`, `/health/ready`, `/status/services` with required vs
  optional dependency classification, graceful degradation, and TCP/disk checks only
  (no learning/ROS2 imports in core health code).
- **Observability:** Prometheus-compatible `/metrics`, structured JSON operational logs,
  stable event names, and per-request `trace_id` middleware (`run_id` in scripts).
- **Dashboard:** Operational status panel with simulation disclaimer and API-unreachable
  fallback (no full dashboard redesign).
- **Evidence:** `scripts/reliability/check_phase7_reliability.py`,
  `scripts/observability/check_phase7_observability.py`, and artifacts under
  `artifacts/reliability/` and `artifacts/observability/`.
- **Docs:** `docs/phase7_reliability.md`, `docs/phase7_observability.md`.

**Not delivered in Phase 7:** mandatory Prometheus/Grafana, heavy OpenTelemetry,
packaging, cloud deployment, Kubernetes, Phase 8 hardware path. Synthetic only — no
real patient data, no medical claims.

### Phase 6B — RL Micro-module (Gymnasium + Stable-Baselines3 PPO, synthetic, on-demand)

Delivered: Phases 1–6A (see below) plus Phase 6B — a lightweight reinforcement
learning micro-module. A tiny Gymnasium environment (`AxonTriageEnvV1`, 10-dim
`Box` observation, `Discrete(6)` actions) simulates *safe operational* triage
decisions (alert prioritization, conservative threshold suggestions, simulated
resource allocation, human-in-the-loop escalation). A short CPU PPO run
(Stable-Baselines3) learns a policy that beats a random baseline under a
transparent `REWARD_V1` reward. Runs log to a local file-based MLflow store
(experiment `axon_rl_micro_module`), produce `rl_report.json` + reward curve +
policy summary + safety envelope, and surface via `/api/learning/rl/*` and a
dashboard RL panel. On-demand only (`learning` profile / `rl-runner`); Gymnasium,
SB3, and torch are isolated from the core profile. The RL policy makes **no
medical decisions**, controls **no real hardware**, and requires human review for
high-risk/low-confidence situations.

Phase 6B precedes Phase 7; it does not modify ROS2/Nav2/SLAM or Phase 6A federated learning.

### Phase 6A — Federated Learning Simulation (Flower + FedAvg, synthetic, on-demand)

Delivered: Phases 1–5.5 (telemetry, edge AI, agents/HITL, MLOps, digital twin +
ROS2 core, and the isolated `ros2-nav-slam` Nav2 + SLAM MiniLab), plus Phase 6A —
a lightweight federated learning simulation. Multiple simulated edge clients
(3–5) each train a tiny CPU MLP (`AxonFLModelV1`, 850 params) on deterministic
synthetic non-IID biosignal-like data; a central coordinator aggregates with
Flower's `FedAvg` (`flwr[simulation]==1.30.0`, stable 1.x). Runs log to a local
file-based MLflow store, produce `federated_report.json` + convergence artifacts,
and surface via `/api/learning/federated/*` and a dashboard FL panel. The FL
experiment is on-demand only (Docker `learning` profile / `fl-runner`); Flower
and torch are isolated from the core profile.

Not delivered: Phase 8 hardware/cloud path, full 3D physics simulation. Synthetic only — no real patient data, no medical claims.

## Forbidden Claims

- Medical-grade monitoring
- Diagnosis of arrhythmia, fatigue, oxygen problems, or clinical conditions
- Production-ready medical device
- Real hospital/clinic deployment
- Autonomous clinical decision-maker
- Enterprise healthcare compliance claims

## Technology Hierarchy

| Layer | Technology | Phase |
|-------|------------|-------|
| Ingress | MQTT / Mosquitto | 1 |
| Buffer / replay | Redis Streams | 1 |
| API | FastAPI + WebSockets | 1 |
| Contracts | Pydantic v2 | 0 |
| Inference | ONNX Runtime | 2 |
| Fusion | Custom fusion service | 2 |
| Agents | LangGraph + LangChain | 3 |
| MLOps | MLflow, fine-tuning, continual learning | 4 |
| Robotics | ROS2 thin adapter | 5 |
| Advanced robotics | Nav2 + SLAM MiniLab | 5.5 |
| Federated / RL | Flower, Gymnasium, SB3 | 6 |
| Observability | Structured logs, `/metrics`, health/status (OTEL/Grafana optional) | 7 |
| Hardware path | ESP32, Pi, Jetson, TinyML (optional) | 8 |
| Portfolio | Case study, demo video | 9 |

## Docker Compose Profile Strategy

| Profile | When |
|---------|------|
| `core` | Default dev (API, Redis, Mosquitto, dashboard, sensor-generators, edge-inference) |
| `sim` | Sensor simulation (Phase 1+) |
| `obs` | Metrics/dashboards (Phase 7) |
| `learning` | MLflow/training (Phase 4+) |
| `ros2` | ROS2 bridge (Phase 5) |
| `ros2-nav-slam` | Nav2 MiniLab (Phase 5.5) |
| `llm` | Optional copilot (Phase 3+) |
| `full` | Late integration demos only |

## How to Avoid Overengineering

- Implement only the current phase
- Keep default Python deps lightweight
- Use placeholders with honest messages, not fake implementations
- Prefer one service per PR over big-bang integration
- Do not add Kubernetes, always-on LLM, or full ROS2 to `core`

## How to Avoid Underbuilding

- Every phase must produce evidence checklist items
- Schemas and topic taxonomy are non-negotiable foundations
- Safety docs and ADRs must exist before agent/ML work
- Tests for real behavior; no hollow README-only features

## What Counts as Evidence

- Reproducible commands with captured output
- Screenshots/videos of working behavior
- Benchmarks with configuration documented
- Model/data cards linked to MLflow runs
- ADRs for architecture decisions
- Trace IDs connecting pipeline stages

## How Future AI Tools Should Behave

1. Read this file and `ROADMAP.md` before coding
2. Respect `.cursor/rules/axon-phase-policy.mdc`
3. Match existing code style and schema contracts
4. Never claim unimplemented features in docs or UI
5. Update evidence checklist when delivering demonstrable output
6. Ask before changing architecture direction — write/update ADRs
7. Keep PRs small and phase-aligned
