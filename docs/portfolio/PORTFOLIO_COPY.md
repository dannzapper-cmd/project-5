# AXON — Reusable Portfolio Copy

Professional copy blocks for project cards, portfolio pages, LinkedIn/GitHub descriptions, and resume bullets. All claims align with Phase 10A evidence and Phase 9 capability matrix.

---

## 1. Short project card

**One sentence**

AXON is a synthetic, local-first Bio-Robotics Edge Command System for simulated rehab robot operations with live telemetry, edge inference, safety-aware agents, and evidence governance.

**Two sentences**

AXON is a reproducible intelligent-systems stack for simulated rehab robot ops: synthetic telemetry, ONNX edge inference, LangGraph agents with HITL, digital twin, and an Evidence Center. It is local-first, Docker Compose–profiled, and backed by automated demo verification and real screenshots — not a medical device.

**Four sentences**

AXON (Autonomous eXecution and Operations Network) demonstrates end-to-end edge AI and IoT operations for a simulated rehabilitation robot scenario using synthetic biomedical-inspired signals only. The stack spans MQTT ingest, Redis Streams, FastAPI/WebSockets, ONNX Runtime inference, safety-aware agents, mission control, digital twin visualization, and observability. Learning loops — synthetic retraining / candidate refresh, federated learning, and RL — run on-demand behind Compose profiles. Phase 10A captured eight real dashboard screenshots and health verification on the core profile; status is PASS WITH DOCUMENTED RISKS.

---

## 2. Portfolio project page

**Title:** AXON — Bio-Robotics Edge Command System

**Subtitle:** Synthetic, local-first command system for simulated rehab robot operations

**Overview**

AXON integrates telemetry, edge-like inference, agent orchestration, human-in-the-loop safety, digital twin state mirroring, and evidence governance in one reproducible local stack. It answers how intelligent systems perceive, decide, learn, and operate under modular activation and honest scope boundaries — with no clinical claims and no real patient data.

**Technical highlights**

- Event-driven spine: MQTT → FastAPI → Redis Streams → WebSocket dashboard
- ONNX Runtime edge inference on synthetic EMG/IMU-like streams
- LangGraph agents + LangChain tools with safety envelope and HITL
- Mission API, deterministic scenarios, Evidence Center index
- Lightweight observability and reliability (health/live/ready, metrics, structured logs)
- MLOps synthetic retraining / candidate refresh (classical models)
- FL (Flower) and RL (Gymnasium PPO) micro-modules — on-demand
- ROS2 thin adapter + Nav2/SLAM MiniLab — compose-validated, profile-gated

**Evidence links**

- [Screenshot index](../evidence/phase10/demo/screenshot-index.md)
- [Demo verification report](../evidence/phase10/demo/demo-verification-report.md)
- [Demo runbook](../evidence/phase10/demo/runbook-phase10a.md)
- [Phase 9 capability matrix](../evidence/phase9_capability_truth_matrix.md)

**Constraints / trade-offs**

- Synthetic-only; not a medical device
- Core demo does not imply live Nav2, FL, or RL unless profiles/scripts are started
- ONNX models generated locally (`make models-generate`)
- Static HTML dashboard for reproducibility over SPA complexity

---

## 3. Resume bullets

Use 5–8 as needed; all are evidence-aligned.

1. Built AXON, a local-first Bio-Robotics Edge Command System integrating MQTT telemetry, Redis Streams, FastAPI/WebSockets, and ONNX inference for simulated rehab robot operations (synthetic signals only).
2. Implemented safety-aware LangGraph agents with human-in-the-loop gates, failure injection, and advisory LLM boundaries — no autonomous clinical or irreversible control paths.
3. Delivered mission control API, deterministic scenario runner, and Evidence Center index with existence-checked artifacts and Phase 9 integrity sealing.
4. Added digital twin state mirroring, lightweight observability (`/metrics`, structured logs), and reliability endpoints (`/health/live`, `/health/ready`) with graceful degradation.
5. Shipped MLOps synthetic retraining / candidate refresh loop for small classical models with drift-aware retrain recommendations — explicitly not neural fine-tuning of a pretrained model.
6. Integrated on-demand federated learning (Flower FedAvg) and RL micro-module (Gymnasium + PPO) behind Docker Compose `learning` profile.
7. Validated ROS2 bridge and headless Nav2/SLAM MiniLab via Compose profiles; documented offline vs live-gated boundaries in demo evidence.
8. Automated Phase 10A demo verification and Playwright screenshot capture (8/8 PNGs) with claim-safety scanner and `verify_phase9.sh` regression gates.

---

## 4. LinkedIn / GitHub pinned description

**AXON** — Bio-Robotics Edge Command System for simulated rehab robot ops. Synthetic, local-first stack: MQTT telemetry, ONNX edge inference, LangGraph agents + HITL, digital twin, Evidence Center. Docker Compose profiles; reproducible demo with real screenshots. Not a medical device. MIT.

---

## 5. Claims-safe tagline options

- A synthetic, local-first command system for simulated rehab robot operations.
- Edge AI + IoT telemetry + safety-aware agents for simulated robotic operations.
- A reproducible portfolio system for real-time telemetry, edge inference, agent traces, and evidence governance.
- Perceive. Decide. Learn. Operate. — with synthetic signals and honest evidence.
- Local intelligent systems demo: telemetry spine, ONNX inference, agents, twin, observability.

---

*See also: [CLAIMS_AND_POSITIONING.md](CLAIMS_AND_POSITIONING.md) · [TECHNICAL_QA.md](TECHNICAL_QA.md)*
