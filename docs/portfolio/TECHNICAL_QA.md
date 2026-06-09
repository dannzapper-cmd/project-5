# AXON — Technical Q&A / Interview Notes

Authentic answers aligned with code, tests, and Phase 10A evidence. Use as speaking notes — adapt wording naturally in conversation.

---

### 1. What is AXON?

AXON is a synthetic-only, local-first Bio-Robotics Edge Command System for **Simulated Rehab Robot Ops**. It ingests synthetic telemetry, runs ONNX edge-like inference, coordinates safety-aware agents with HITL, mirrors state in a digital twin, and maintains an Evidence Center. It is a full systems portfolio project — not a chatbot or medical product.

---

### 2. Why simulated data?

AXON uses no real patient data because identifiable health records introduce privacy, regulatory, and ethical barriers inappropriate for a public portfolio repo. Synthetic biomedical-inspired streams let me demonstrate ingestion, validation, inference, fusion confidence, replay, and failure injection with reproducible seeds — while keeping claims honest and scope safe.

---

### 3. Is this a medical device?

**No.** AXON does not diagnose, treat, or monitor real patients. It performs operational anomaly detection on synthetic signals for a simulated robot scenario. Docs, UI disclaimers, and `scan_claims.py` enforce that boundary.

---

### 4. What runs locally?

On the default **`core` profile:** Mosquitto, Redis, FastAPI, sensor generators, edge-inference, and the static dashboard. Optional profiles add observability stacks, MLflow, ROS2 bridge, Nav2 MiniLab, and real LLM — each started explicitly.

---

### 5. Why Docker Compose profiles instead of Kubernetes?

The goal is reproducible local demos and modular staging, not multi-tenant production orchestration. Compose profiles express which heavy subsystems are active without implying everything runs at once — a better honesty match for a portfolio artifact.

---

### 6. Why MQTT and Redis Streams?

MQTT is lightweight for many synthetic sensor topics. Redis Streams give durable buffering and replay alignment with simple local ops — no Kafka cluster for a laptop demo. Both fit the event-driven spine story.

---

### 7. What does edge-like inference mean here?

ONNX Runtime scores features on the inference service in the local Compose stack — emulating an edge inference path without claiming deployed hospital edge hardware. Models are small and generated via `make models-generate`.

---

### 8. How does sensor fusion work at a high level?

Operational confidence is aggregated in the **twin path** (mean-confidence style). A standalone `fusion-service` folder is a documented placeholder — I do not claim a full fusion microservice is implemented.

---

### 9. What role do agents play?

LangGraph orchestrates multi-step agent flows; LangChain provides tools and retrieval. Agents propose operational responses (alerts, pauses, escalations) inside a safety module. They consume live telemetry and model scores — they are not free-form chat endpoints driving the stack.

---

### 10. Does the LLM control the system?

**No.** Default mode uses a mock LLM. Optional real LLM mode is advisory. Irreversible or high-risk actions go through safety rules and HITL confirmation. The LLM does not bypass the safety envelope.

---

### 11. What is HITL doing?

Human-in-the-loop gates mark decisions that need human confirmation when confidence is low or risk is high. The dashboard surfaces decision events and trace metadata so a human operator (simulated in demo) would approve or reject before execution.

---

### 12. What evidence proves the demo works?

Phase 10A: `phase10a_verify_demo.sh` health table, 8/8 Playwright screenshots in `docs/evidence/phase10/demo/screenshots/latest/`, capture metadata JSON, demo verification report, and passing claim scan on demo docs. See [demo-verification-report.md](../evidence/phase10/demo/demo-verification-report.md).

---

### 13. What does PASS WITH DOCUMENTED RISKS mean?

Core demo automation and screenshots passed, but known limitations are recorded — not hidden. Examples: ROS2/Nav2 offline in core-only captures, FL/RL/MLOps artifact-only unless on-demand scripts run, ONNX models not in git, dashboard `inactive` in API service map for static file server.

---

### 14. What are the known limitations?

- Nav2/SLAM live runtime not part of default demo
- FL/RL/MLOps require explicit profile or Make targets
- Fusion service is placeholder-level
- Static HTML dashboard (no SPA build pipeline)
- Full test suite not re-run on every doc-only change — targeted gates instead
- No cloud deployment, release tags, or video in Phase 10B

---

### 15. What would you improve with more time/hardware?

Optional cloud artifact hosting, richer replay scenarios, polished dashboard visuals without losing reproducibility, one-command on-demand profile demos, and a real fusion subsystem if scope expands. I would not frame the current artifact as incomplete — it is scope-bounded and evidence-backed.

---

### 16. What did you automate?

Health verification script, Playwright screenshot capture (Python primary path), PNG validator, claim scanner, `verify_phase9.sh` evidence index checks, CI smoke, and Make targets for MLOps/FL/RL/Nav2 demos.

---

### 17. How would this evolve toward real hardware?

Replace synthetic generators with hardware adapters behind the same Pydantic contracts; add calibration and device auth; tighten safety interlocks and audit logging; run HITL as a first-class operator workflow; only then consider regulated contexts — with an entirely separate compliance program. AXON deliberately stops at simulated ops.

---

### 18. How did you avoid unsafe biomedical claims?

Safety policies in `docs/safety/`, UI simulation disclaimers, negation-aware `scan_claims.py`, capability truth matrix, and explicit README positioning. MLOps described as synthetic retraining / candidate refresh — not clinical AI product language.

---

### 19. How would you debug a runtime failure?

Check `docker compose --profile core ps`, API `/health/ready` and `/status/services`, telemetry counters, service logs (`docker compose logs api edge-inference`), Redis stream lengths, and whether `make models-generate` was run. Phase 10A runbook has a troubleshooting table.

---

### 20. How does this project compare to a normal AI app?

A typical AI app might expose one model endpoint or chat UI. AXON wires **telemetry transport, buffering, inference, agents, safety, twin, mission evidence, observability, and optional learning loops** with profile-based modularity. The engineering story is integration, boundaries, and proof — not a single prompt chain.

---

*Related: [AXON_CASE_STUDY.md](AXON_CASE_STUDY.md) · [CLAIMS_AND_POSITIONING.md](CLAIMS_AND_POSITIONING.md)*
