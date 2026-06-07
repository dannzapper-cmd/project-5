# ADR-011: Phase 6A — Federated Learning with Flower + FedAvg (synthetic, on-demand)

## Status

Accepted

## Context

Phase 6 introduces the learning layer's distributed-training story. Phase 6A
delivers the **federated learning** half (Phase 6B RL is explicitly out of scope
for this PR). AXON is a local-first, evidence-driven, synthetic portfolio project
for *Simulated* Rehab Robot Ops. We need to demonstrate that multiple simulated
edge nodes can train locally on biosignal-like data and aggregate a shared model
— without real patient data, heavyweight always-on services, hardware, cloud, or
medical claims.

## Decision

- **Framework: Flower (`flwr`) 1.x, pinned to `flwr[simulation]==1.30.0`.** This
  is the current stable 1.x line and is compatible with the repo's Python (3.11/
  3.12; Flower needs >= 3.10). We use the stable simulation entrypoint
  `flwr.simulation.start_simulation` with the `Context`-based `client_fn`
  signature, plus the built-in `flwr.server.strategy.FedAvg`. No Flower 2.x or
  experimental APIs. This is real Flower client/server simulation, not a manual
  for-loop. (The newer `run_simulation` + `ClientApp`/`ServerApp` path hung under
  this sandbox's gRPC/Ray configuration; `start_simulation` is reliable and
  fully supported in 1.x.)
- **Aggregation: FedAvg**, the canonical, well-understood baseline. Per-round
  global metrics are computed centrally on a fixed held-out set so results are
  reproducible regardless of Ray scheduling.
- **Model: a tiny CPU MLP, `AxonFLModelV1`** — input_dim=8, hidden=[32, 16],
  output=2 (normal/anomaly), 850 parameters (< 1000). No CNN/Transformer.
- **Synthetic data only.** 3–5 simulated edge clients, each with a deterministic,
  statistically distinct (non-IID) biosignal-like distribution (EMG/ECG/IMU/SpO2
  proxies). No real or clinical datasets are downloaded or used. SpO2 "missing
  readings" are encoded safely via an explicit `spo2_missing_ratio` feature.
- **Reproducibility.** Seeds (`random`, `numpy`, `torch`) are set before data
  generation and training; each client uses `client_seed = FL_SEED + client_index`
  (default `FL_SEED=42`). Same seed → same report (except timestamps); different
  seed → different results.
- **MLflow logs to a local `file:` store by default** — no server required. The
  `learning` profile optionally exposes the MLflow UI.
- **On-demand learning profile.** The FL experiment is triggered manually (CLI /
  Makefile / one-shot `fl-runner` container). It never auto-starts with the API/
  core and uses no always-on background training thread. Flower/torch deps are
  isolated to `requirements-learning.txt` / the `federated` extra and the
  `learning` Docker profile.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Manual FedAvg for-loop | Not real federated learning; explicitly disallowed |
| Flower 2.x / `run_simulation` only | Hung in sandbox; 2.x/experimental APIs out of scope |
| Real/clinical datasets | Violates synthetic-only, no-real-data boundary |
| Large NN (CNN/Transformer) | Not CPU-friendly; unnecessary for the demo |
| Always-on training service | Bloats core; violates on-demand profile strategy |
| Remote MLflow / cloud tracking | Adds network + account dependency |

## Consequences

- A reproducible federated experiment produces `federated_report.json`,
  `client_distribution_summary.json`, `convergence.{json,csv}`, a model/data
  card, and a local MLflow run. Default 5-client/5-round run shows clear
  convergence (global loss decreases, accuracy rises).
- The dashboard and `/api/learning/federated/*` endpoints expose live FL status
  from the generated artifacts (idle before any run), reading real data — never
  hardcoded metrics.
- CI stays light: FL-engine tests skip when Flower/torch are absent; the API/
  safety tests run in core CI.

## Not Doing (Scope Boundaries)

- **No RL / Phase 6B** in this PR.
- **No Phase 7** observability expansion.
- No real patient data, no clinical datasets, no medical claims, no diagnosis.
- No production/real federated server, no cross-device deployment.
- No hardware dependency, no cloud requirement, no giant models.
- No changes to ROS2 / Nav2 / SLAM.
