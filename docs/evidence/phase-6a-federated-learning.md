# Phase 6A — Federated Learning Simulation (Flower + FedAvg)

> **Synthetic federated learning simulation. No real patient data. No medical claims.**
>
> This is not medical diagnosis, not clinical monitoring, and not trained on real
> patients. It is a synthetic portfolio simulation for edge/federated learning
> architecture. Model output is an operational/anomaly *simulation* only.

## Overview

Phase 6A adds a lightweight, reproducible **federated learning** simulation to
AXON. Multiple simulated edge nodes ("edge clients") each train a tiny CPU MLP
(`AxonFLModelV1`) on their own synthetic, non-IID, biosignal-like dataset. A
central coordinator aggregates the model updates with **Flower's FedAvg**
strategy. Everything is deterministic, local-first, on-demand, and logged to a
local file-based MLflow store.

Phase 6A does **not** implement RL (Phase 6B) and does **not** start Phase 7.

## Flower / FedAvg

- **Flower (`flwr`) `1.30.0`** (`flwr[simulation]`), stable 1.x — no 2.x or
  experimental APIs. Python >= 3.10 required (repo runs 3.11/3.12).
- Simulation entrypoint: `flwr.simulation.start_simulation` with a
  `Context`-based `client_fn`; aggregation: `flwr.server.strategy.FedAvg`.
- This is real Flower client/server simulation (clients run as Ray actors), not
  a manual for-loop. Per-round **global** metrics are computed centrally on a
  fixed held-out set, so the report is reproducible.

## Synthetic edge clients (non-IID, deterministic)

| Client | Signal focus | Pattern |
|--------|--------------|---------|
| `edge-client-01` | `emg_fatigue_noise` | EMG-heavy, high variance, spikes |
| `edge-client-02` | `ecg_drift_spike` | ECG-like drift/spike, lower variance |
| `edge-client-03` | `imu_movement_dropout` | IMU movement spike + dropout |
| `edge-client-04` | `spo2_low_missing` | SpO2-proxy low-signal / missing ratio |
| `edge-client-05` | `mixed_multi_anomaly` | Mixed multi-anomaly (optional 5th) |

8 features (fixed order): `emg_mean, emg_variance, ecg_mean, ecg_variance,
imu_magnitude, imu_variance, spo2_mean, spo2_missing_ratio`. Labels: `0 = normal`,
`1 = anomaly`. Each client uses `client_seed = FL_SEED + client_index`
(default `FL_SEED=42`). SpO2 "missing readings" are encoded **safely** via the
explicit `spo2_missing_ratio` feature — no real or clinical data, ever.

## Model: `AxonFLModelV1`

Tiny MLP: `Linear(8,32) → ReLU → Linear(32,16) → ReLU → Linear(16,2)` =
**850 parameters** (< 1000). CPU-only. No CNN/Transformer/large model.

## How to reproduce locally

```bash
# 1) Install FL deps (isolated from core; CPU torch + Flower 1.x + MLflow)
make learning-install
#    equivalently:
#    pip install torch --index-url https://download.pytorch.org/whl/cpu
#    pip install -r requirements-learning.txt

# 2) Run the federated simulation (default 3 clients, 5 rounds, 3 local epochs)
make learning-fl-run
#    or with 5 clients:
#    python scripts/run_federated_learning.py --num-clients 5 --num-rounds 5 --local-epochs 3 --seed 42

# 3) Inspect the report + convergence
make learning-fl-report
cat artifacts/learning/federated/convergence.csv

# 4) View MLflow UI (optional, learning profile)
docker compose --profile learning up mlflow    # -> http://localhost:5001
#    or locally:  mlflow ui --backend-store-uri ./artifacts/mlops/mlruns

# 5) API status (with the core API running)
make fl-status
#    curl http://localhost:8000/api/learning/federated/status
```

## Example evidence (5 clients, 5 rounds, seed 42)

Convergence (`convergence.csv`) — global loss decreases, accuracy rises:

```
round,global_loss,global_accuracy
0,0.710497,0.394521
1,0.668317,0.605479
2,0.645521,0.605479
3,0.587346,0.605479
4,0.545883,0.652055
5,0.269330,0.945205
```

Per-client final summary (final global model evaluated on each client):

| Client | Signal | Final local loss | Final local acc |
|--------|--------|------------------|-----------------|
| edge-client-01 | emg_fatigue_noise | 0.237 | 1.000 |
| edge-client-02 | ecg_drift_spike | 0.279 | 0.957 |
| edge-client-03 | imu_movement_dropout | 0.398 | 0.754 |
| edge-client-04 | spo2_low_missing | 0.218 | 1.000 |
| edge-client-05 | mixed_multi_anomaly | 0.249 | 0.967 |

(Exact values are reproducible for a fixed seed; timestamps differ.)

## Artifacts

Written to `artifacts/learning/federated/` (runtime outputs are gitignored):

- `federated_report.json` — full run report (schema below)
- `client_distribution_summary.json` — per-client feature mean/std summary
- `convergence.json` / `convergence.csv` — per-round global metrics
- `model_card_axon_fl_v1.md` — model/data card
- `status.json` — idle/running/completed/failed marker
- `runs/<experiment_id>.json` — archived per-run reports (for `/history`)

MLflow run logged to `artifacts/mlops/mlruns/` under experiment
`axon_federated_learning`.

### `federated_report.json` schema (required fields)

`experiment_id`, `timestamp_utc`, `seed`, `num_clients`, `num_rounds`,
`local_epochs`, `model_type` (`"AxonFLModelV1"`), `global_results[]`
(`round`, `global_loss`, `global_accuracy`), `client_summaries[]`
(`client_id`, `data_size`, `signal_type`, `final_local_loss`),
`mlflow_run_id` (string or null), `disclaimer`.

## Dashboard

The dashboard renders a **Federated Learning** panel showing run status, number
of edge clients, completed rounds, latest global loss/accuracy, per-client
summary, a convergence table, the MLflow run id, and the report path. The
disclaimer *"Synthetic federated learning simulation. No real patient data. No
medical claims."* is always visible (even before any run) and is read from the
API — never hardcoded.

## API

- `GET /api/learning/federated/status` — compact status (`FederatedStatusV1`),
  valid before (idle) and after (completed) a run.
- `GET /api/learning/federated/latest` — full latest result (`FederatedResultV1`)
  with the convergence curve and client distribution summary.
- `GET /api/learning/federated/history` — recent run summaries.

## Docker / profiles

- `docker compose --profile core config` — Flower/torch absent (isolation).
- `docker compose --profile learning config` — `fl-runner` (one-shot) + `mlflow`.
- The FL experiment is triggered manually; it never auto-starts with core and
  uses no always-on background training.

## Expected tests

```bash
pytest tests/phase6a/            # FL engine tests (skip if Flower/torch absent)
bash scripts/verify_phase6a.sh   # lint + tests + smoke + schema + compose + safety + ROS2 freeze
```

## Known limitations / troubleshooting

- **Ray noise:** Flower's Ray backend prints deprecation/info lines; these are
  cosmetic. The CLI suppresses most via `RAY_DEDUP_LOGS`.
- **Determinism:** runs use `num_cpus=1` (serial Ray) so per-round aggregation
  order — and thus the report — is reproducible for a fixed seed.
- **Convergence is honest, not hardcoded:** early rounds can be flat before the
  model crosses the decision boundary; the default 5-round run converges. Tune
  `--num-rounds` / `--local-epochs` / `--learning-rate` if you change the data.
- **torch wheel size:** install the CPU-only wheel
  (`--index-url https://download.pytorch.org/whl/cpu`) to keep it light.

## Scope boundaries

No RL / Phase 6B. No Phase 7. No real patient data. No medical claims. No
hardware dependency. No cloud requirement. No giant models. No ROS2/Nav2/SLAM
changes.
