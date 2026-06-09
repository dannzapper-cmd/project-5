# AXON Roadmap

**AXON — Bio-Robotics Edge Command System**  
*Perceive. Decide. Learn. Operate.*

Phased delivery for Simulated Rehab Robot Ops. **Phase 0 does not implement runtime capabilities.**

---

## Phase 0: Product Contract and Repo Foundation

**Goal:** Establish repo skeleton, contracts, architecture docs, safety boundaries, and Compose profiles.

**Required outputs:**
- README, ROADMAP, PROJECT_CONTEXT, CONTRIBUTING
- Pydantic event schemas and topic taxonomy
- ADRs (001 complete; 002–005 placeholders)
- Docker Compose profiles
- FastAPI health endpoint
- Dashboard placeholder
- Tests and dev check script

**What must be real:**
- Schema validation tests
- Health API response
- Compose config validation

**What can be simulated:**
- N/A (no runtime pipeline)

**Evidence to collect:**
- Repo skeleton screenshot
- Architecture diagram screenshot
- `make compose-config` proof
- Health check screenshot
- Dashboard placeholder screenshot

**Acceptance criteria:**
- `make test` and `make dev-check` pass
- `docker compose --profile core config` succeeds
- No false claims of telemetry/ML/agent capabilities
- All service folders have honest placeholder READMEs

---

## Phase 1: Telemetry Spine

**Goal:** Synthetic sensor generators → MQTT → FastAPI → Redis Streams → WebSocket → dashboard.

**Required outputs:**
- Sensor generator service(s)
- MQTT ingest in API
- Redis Streams producers/consumers
- WebSocket broadcast channels
- Replay mode foundation

**What must be real:**
- MQTT publish/subscribe with Pydantic payloads
- Redis Stream append and read
- WebSocket live updates to dashboard

**What can be simulated:**
- All biomedical and robot signals (synthetic generators)

**Evidence to collect:**
- Telemetry video
- MQTT topic proof
- Redis Streams proof
- WebSocket live update proof

**Acceptance criteria:**
- End-to-end trace_id propagation from sensor to dashboard
- Replay reproduces a recorded session segment
- Topic taxonomy fully exercised

---

## Phase 2: Edge AI Core

**Goal:** ONNX Runtime inference, sensor fusion, model score events.

**Required outputs:**
- Edge inference service
- Fusion service
- At least one ONNX model path (tiny classifier or autoencoder)
- Model latency benchmarks

**What must be real:**
- ONNX Runtime inference with measured latency
- Fusion confidence output

**What can be simulated:**
- Training data (synthetic)
- Model inputs from Phase 1 generators

**Evidence to collect:**
- ONNX inference proof
- Model latency benchmark
- Fusion confidence screenshot
- Missing-data scenario proof

**Acceptance criteria:**
- `ModelScoreEventV1` flows to Redis and WebSocket
- Fusion handles missing channels without silent repair

---

## Phase 3: Agents + Safety with LangGraph and LangChain

**Goal:** Stateful agent orchestration, LangChain tools/RAG, HITL safety workflows.

**Required outputs:**
- LangGraph agent runtime
- LangChain tool and retriever integrations
- Decision and agent trace events
- HITL confirmation flow in dashboard
- Failure injection scenarios

**What must be real:**
- LangGraph traces with step-level evidence
- Human confirmation gate for high-risk decisions

**What can be simulated:**
- Operator responses
- Rehab session context

**Evidence to collect:**
- LangGraph trace screenshot
- LangChain tool/RAG evidence
- HITL decision screenshot
- Failure injection demo
- Replay mode demo

**Acceptance criteria:**
- `requires_human_confirmation` enforced in simulation
- Agent traces link to fusion and model score events via trace_id

---

## Phase 4: MLOps + Synthetic Retraining + Drift-Triggered Retraining

**Goal:** MLflow tracking, synthetic retraining / candidate refresh loop, drift-triggered retraining recommendation.

AXON includes a synthetic retraining / candidate refresh loop for small classical models. It is not fine-tuning of a pretrained neural network.

**Required outputs:**
- MLflow integration
- Synthetic retraining / candidate refresh scripts for at least one model
- Drift-triggered retraining recommendation documentation

**What must be real:**
- MLflow runs with artifacts
- Before/after metric comparison

**What can be simulated:**
- Drift injection in synthetic streams

**Evidence to collect:**
- MLflow run screenshot
- Synthetic retraining / candidate refresh before/after report
- Drift-triggered retraining recommendation evidence

**Acceptance criteria:**
- Reproducible training command documented in runbook
- Model cards updated with metrics

---

## Phase 5: Digital Twin + ROS2 Core

**Goal:** Dashboard digital twin, ROS2 thin adapter, robot state mirroring.

**Required outputs:**
- Digital twin visualization
- ROS2 bridge service
- ROS2 topic/service integration per taxonomy

**What must be real:**
- ROS2 topic publish/subscribe
- Digital twin reflects live robot state

**What can be simulated:**
- Robot kinematics and session

**Evidence to collect:**
- ROS2 topic evidence
- ROS2 service/action evidence
- Digital twin live mirror video

**Acceptance criteria:**
- `/axon/robot/state` and fusion state visible in twin
- Safety service stub for operator confirmation

---

## Phase 5.5: Full ROS2 Nav2 + SLAM MiniLab (Mandatory Advanced)

**Goal:** Isolated advanced lab demonstrating Nav2 navigation and SLAM for rehab route execution.

> **This phase is mandatory, not optional.**

**Required outputs:**
- `ros2-nav-slam` profile stack
- Nav2 configuration for simulated robot
- SLAM map generation
- `/axon/nav/execute_rehab_route` action

**What must be real:**
- Nav2 planning and execution in simulation
- SLAM map artifact

**What can be simulated:**
- Environment map and robot

**Evidence to collect:**
- Nav2 + SLAM MiniLab video or screenshot
- Route execution with safety pause

**Acceptance criteria:**
- MiniLab runs independently of `core` daily dev profile
- Documented setup runbook with exact commands

---

## Phase 6: Federated Learning + RL

**Goal:** Flower federated rounds and RL micro-module with Gymnasium/SB3.

**Required outputs:**
- Flower client/server skeleton
- RL environment for rehab scenario micro-decisions
- Training curves

**What must be real:**
- At least one Flower convergence run
- At least one RL reward curve

**What can be simulated:**
- Federated nodes (local processes)

**Evidence to collect:**
- Flower convergence chart
- RL reward curve

**Acceptance criteria:**
- Reproducible commands for both loops
- Evidence linked from model cards

---

## Phase 7: Observability + Reliability

**Goal:** OpenTelemetry traces, Prometheus metrics, Grafana dashboards, failure/replay hardening.

**Required outputs:**
- OTel instrumentation across API and services
- Prometheus scrape targets
- Grafana dashboards
- Memory/CPU profiling report

**What must be real:**
- Trace spanning ingest → inference → agent
- Dashboard panels with live metrics

**What can be simulated:**
- Load via synthetic generators

**Evidence to collect:**
- OTel trace evidence
- Prometheus/Grafana screenshots
- Memory/CPU profile

**Acceptance criteria:**
- `obs` profile starts without `full`
- Runbook for common failure scenarios

**Delivery note (implemented):** Lightweight local reliability/observability layer —
health/readiness/service status, `/metrics`, structured logs, dashboard operational
panel, scripts + artifacts. Prometheus/Grafana and heavy OTEL remain optional/future;
not required for Phase 7 completion.

---

## Phase 8 — Integrated Mission Control System

**Goal:** Unify prior phases into a mission control cockpit with end-to-end operational
loop visibility, scenario runner, timeline, Evidence Center, and dashboard integration.

**Required outputs:**
- Mission API (`/mission/*`)
- Deterministic scenario runner + `artifacts/phase8/` evidence
- Dashboard Mission Control section
- Phase 8 tests + verify script + ADR-013

**What must be real:**
- Mission status/timeline/evidence APIs with honest degradation
- Scenario artifacts with required JSON fields (seed 42)
- Evidence index with file existence checks

**What can be simulated:**
- ROS2/Nav2/SLAM runtime (artifact/status fallback)
- FL/RL without retraining (existing artifacts)

**Evidence to collect:**
- `artifacts/phase8/phase8_mission_*.json`
- Scenario summary + mission timeline artifact
- Dashboard Mission Control panel (API-connected or fallback)

**Acceptance criteria:**
- `pytest tests/phase8/ -q` passes
- `bash scripts/verify_phase8.sh` passes
- Docker compose profiles validate (core, learning, ros2, ros2-nav-slam, obs)
- No medical claims; no fake evidence

**Next:** Phase 9 — final QA, repair, hardening before packaging.

---

## Phase 9 — QA, Repair, and Hardening

**Goal:** Senior verification-driven repair before portfolio packaging. No new subsystems.

**Required outputs:**
- `scripts/verify_phase9.sh` + `scripts/scan_claims.py`
- Evidence integrity repairs (honest index paths, runtime artifact hygiene)
- Phase 9 verification and capability truth reports

**Acceptance criteria:**
- `bash scripts/verify_phase9.sh` passes (Block 1; Block 2 when Docker available)
- `make lint` and `make test` pass
- No unqualified fine-tuning or medical-device claims
- No fake evidence committed

**Next:** Phase 10 — portfolio packaging.

---

## Phase 8 (legacy note) — Cloud/VM + Hardware Path

*Superseded for portfolio delivery order — hardware/cost report may return in a later
optional track. Phase 8 as shipped integrates mission control, not cloud packaging.*

**Goal:** Document and optionally demonstrate cloud VM profiles and edge hardware paths.

**Required outputs:**
- Cost/hardware report (measured)
- Optional ESP32 / Pi / Jetson / TinyML path docs
- Profile recommendation matrix

**What must be real:**
- Measured resource usage per profile

**What can be simulated:**
- Hardware if devices unavailable

**Evidence to collect:**
- Cost/hardware report
- Optional hardware demo artifacts

**Acceptance criteria:**
- `docs/cost-hardware/local-vs-cloud-profiles.md` completed with measurements
- No specific RAM mandates in docs

---

## Phase 10: Portfolio Packaging

**Goal:** Final demo, case study, interview narrative, Evidence Center completion.

**Required outputs:**
- End-to-end demo video
- Portfolio case study document
- Interview narrative
- Completed evidence checklist review

**What must be real:**
- Reproducible `full` profile demo command

**What can be simulated:**
- Scenario narratives

**Evidence to collect:**
- Final demo video
- Portfolio case study
- Interview narrative

**Acceptance criteria:**
- All mandatory phase evidence items checked or explicitly waived with reason
- README accurately reflects shipped capabilities
