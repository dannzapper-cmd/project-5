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

**Phase 3 — Agents + Safety**

Delivered: Phase 2 edge AI plus LangGraph agent orchestration, LangChain tools/RAG, DecisionEventV1, AgentTraceEventV1, Redis HITL, mock/real LLM copilot, dashboard agent panels, failure injection.

Not delivered: sensor fusion, ML training, ROS2, digital twin 3D, full Redis replay consumers.

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
| Observability | OpenTelemetry, Prometheus, Grafana | 7 |
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
