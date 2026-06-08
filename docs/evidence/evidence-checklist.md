# Evidence Checklist

Track demonstrable proof across AXON phases. Check items only when reproducible evidence exists.

## Phase 0 — Foundation

- [ ] Repo skeleton screenshot
- [ ] Architecture diagram screenshot
- [ ] Docker Compose profile validation proof (`make compose-config`)
- [ ] API health check screenshot (`GET /health`)
- [ ] Dashboard placeholder screenshot

## Phase 1 — Telemetry Spine

- [ ] Core profile starts (`docker compose --profile core up --build`)
- [ ] Sensor generator logs show publishing
- [ ] MQTT topics receive events (`mosquitto_sub -t 'axon/v1/sensors/#' -v`)
- [ ] API validates events (`/telemetry/status` counters increase)
- [ ] Redis Streams contain events (`redis-cli XLEN axon:v1:stream:sensors:emg`)
- [ ] WebSocket dashboard receives live events
- [ ] Dashboard screenshot with 5 live streams (EMG, ECG-like, IMU, SpO2-proxy, robot_state)
- [ ] Telemetry video (synthetic streams)
- [ ] Replay `normal_session` works (`make replay-normal`)
- [ ] Replay `sensor_dropout` works (`make replay-dropout`)
- [ ] Invalid event is rejected safely (invalid_events counter)
- [ ] No medical claims in UI/docs review

## Phase 2 — Edge AI Core

- [ ] ONNX model files generated (`make models-generate`)
- [ ] Model metadata files present (`models/metadata/`)
- [ ] Benchmark report generated (`docs/evidence/phase2-inference-benchmark.md`)
- [ ] Model score stream has events (`XLEN axon:v1:stream:model_scores`)
- [ ] Dashboard shows model score panels
- [ ] Latency p50/p95 captured in benchmark report
- [ ] No medical claims in labels/UI/docs review

## Phase 3 — Agents + Safety

- [ ] LangGraph decision trace screenshot
- [ ] LangChain tool/RAG/retriever evidence
- [ ] Human-in-the-loop decision screenshot
- [ ] Failure injection demo
- [ ] Replay mode demo (full Redis consumer replay)

## Phase 4 — MLOps

- [ ] MLflow run screenshot
- [ ] Fine-tuning before/after report
- [ ] Continual learning drift trigger evidence

## Phase 6 — Federated Learning + RL

### Phase 6A — Federated Learning (delivered)

- [x] FL deps installed (`make learning-install`)
- [x] Federated simulation runs (`make learning-fl-run`) — 3–5 synthetic edge clients
- [x] `federated_report.json` produced with required schema fields
- [x] Convergence captured (`artifacts/learning/federated/convergence.csv`) — global loss decreases
- [x] Flower FedAvg used (`framework: flower==1.30.0`, `strategy: FedAvg` in report)
- [x] MLflow run logged locally (`mlflow_run_id` in report; `mlflow ui` under learning profile)
- [x] API status before/after run (`make fl-status` / `GET /api/learning/federated/status`)
- [x] Dashboard Federated Learning panel screenshot (status, clients, rounds, metrics, disclaimer)
- [x] Phase 6A tests pass (`pytest tests/phase6a/`)
- [x] `docker compose --profile core config` passes (no Flower/torch in core)
- [x] `docker compose --profile learning config` passes (`fl-runner` present)
- [x] No medical claims; synthetic-only disclaimer visible in UI

### Phase 6B — RL Micro-module (delivered)

- [x] RL deps installed (`make learning-rl-install`) — Gymnasium 0.29.1 + SB3 2.3.2
- [x] `AxonTriageEnvV1` Gymnasium env (10-dim `Box`, `Discrete(6)`); `check_env` passes
- [x] RL experiment runs (`make learning-rl-run`) — PPO vs random baseline
- [x] `rl_report.json` produced with required schema fields (`reward_version: REWARD_V1`)
- [x] Trained policy beats baseline (seed 42: 75.4 vs 0.54; improvement ≈ 138×)
- [x] Operational safety metrics real (unsafe-action rate ≈ 0.0; HITL rate ≈ 0.32)
- [x] Reward curve captured (`artifacts/learning/rl/reward_curve.csv`) — rises monotonically
- [x] MLflow run logged locally (`mlflow_run_id` in report; experiment `axon_rl_micro_module`)
- [x] Reproducible: same seed → identical metrics; different seed → different metrics
- [x] API status before/after run (`make rl-status` / `GET /api/learning/rl/status`)
- [x] Dashboard RL Micro-module panel (status, rewards, rates, reward curve, disclaimer)
- [x] Phase 6B tests pass (`RL_CI_MODE=true pytest tests/phase6b/`)
- [x] `docker compose --profile core config` passes (no Gymnasium/SB3/torch in core)
- [x] `docker compose --profile learning config` passes (`rl-runner` coexists with `fl-runner`)
- [x] Safety envelope + exact disclaimer visible; no medical claims

## Phase 5 — ROS2 Core

- [ ] ROS2 topic evidence
- [ ] ROS2 service/action evidence
- [ ] Digital twin live state mirror video

## Phase 5.5 — Nav2 + SLAM MiniLab (Mandatory)

- [ ] Nav2 + SLAM MiniLab video or screenshot

## Phase 7 — Observability

- [ ] OpenTelemetry trace evidence
- [ ] Prometheus/Grafana evidence
- [ ] Memory/CPU profile

## Phase 8 — Hardware / Cost

- [ ] Cost/hardware report

## Phase 9 — Portfolio

- [ ] Final demo video
- [ ] Portfolio case study
- [ ] Interview narrative
