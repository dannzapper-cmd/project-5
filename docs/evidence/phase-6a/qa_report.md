# Phase 6A Local QA Report

> Synthetic federated learning simulation. No real patient data. No medical claims.

## Summary

- Branch: `feat/phase-6a-federated-learning`
- Local QA date: 2026-06-07
- Verdict: PASS WITH FIXES
- Scope: Phase 6A Federated Learning Simulation only. No RL / Phase 6B. No Phase 7.

## Commands Run

```bash
git checkout main
git pull origin main
git fetch origin
git checkout feat/phase-6a-federated-learning
git pull origin feat/phase-6a-federated-learning
git status
git log --oneline -10
git diff main...HEAD --stat
docker compose --profile core config
docker compose --profile learning config
docker compose --profile core config 2>&1 | rg -i "flwr|flower|torch|ray" || true
make test
.venv/bin/pytest tests/ -v
.venv/bin/ruff check .
make learning-install
.venv/bin/python -c "import flwr; print(flwr.__version__)"
.venv/bin/python -c "from flwr.client import NumPyClient; from flwr.server.strategy import FedAvg; print('Flower API imports OK')"
.venv/bin/python -c "import sys; sys.modules['flwr']=None; sys.modules['torch']=None; from apps.api.main import app; print('FastAPI imports without flwr/torch: OK')"
bash scripts/verify_phase6a.sh
FL_SEED=42 make learning-fl-run
docker compose stop mlflow 2>/dev/null || true
rm -rf artifacts/mlops/mlruns
FL_NUM_CLIENTS=5 FL_SEED=42 make learning-fl-run
docker compose --profile core down
docker compose --profile core up --build -d
curl http://localhost:8000/health
curl http://localhost:8000/api/learning/federated/status
curl http://localhost:8000/api/learning/federated/latest
curl http://localhost:8000/api/learning/federated/history
FL_NUM_CLIENTS=5 FL_SEED=42 make learning-fl-run
cp artifacts/learning/federated/federated_report.json /tmp/report_seed42_a.json
FL_NUM_CLIENTS=5 FL_SEED=42 make learning-fl-run
cp artifacts/learning/federated/federated_report.json /tmp/report_seed42_b.json
FL_NUM_CLIENTS=5 FL_SEED=123 make learning-fl-run
cp artifacts/learning/federated/federated_report.json /tmp/report_seed123.json
docker compose --profile ros2 config
docker compose --profile ros2-nav-slam config
git diff main...HEAD -- ros2_ws/ robotics/ services/ros2-bridge services/ros2-nav-slam-minilab
docker compose --profile core ps
docker compose --profile core logs --tail=200
docker compose --profile learning build fl-runner
```

## Results

- `make test`: PASS — 147 passed, 3 warnings after learning dependencies were installed.
- `pytest tests/ -v`: PASS — 134 passed, 1 skipped, 2 warnings before learning dependencies were installed; Phase 6A Flower tests later ran in `make test`.
- `ruff check .`: FAIL outside Phase 6A due to pre-existing lint issues in `services/edge-inference`, `services/ros2-bridge`, and `services/ros2-nav-slam-minilab`. Phase 6A scoped lint in `scripts/verify_phase6a.sh` passed.
- `scripts/verify_phase6a.sh`: PASS when run outside the Cursor sandbox. The sandboxed run failed because Ray/psutil could not call macOS `sysctl`.
- Docker core config: PASS.
- Docker learning config: PASS.
- Docker learning profile: PASS — `fl-runner` built successfully, ran as a one-shot container, and MLflow UI served on `localhost:5001` with a healthy container healthcheck.
- Core dependency isolation: PASS — no `flwr`, Flower, torch, or Ray in `docker compose --profile core config`.
- FastAPI import isolation: PASS — `apps.api.main` imports with `sys.modules['flwr'] = None` and `sys.modules['torch'] = None`.
- Flower API: PASS — `flwr==1.30.0`, `NumPyClient`, and `FedAvg` import successfully.
- `AxonFLModelV1`: PASS — 850 trainable parameters.
- Core rebuild + health: PASS — `GET /health` returned HTTP 200 after `docker compose --profile core up --build -d`.
- API endpoints: PASS — `/api/learning/federated/status`, `/latest`, and `/history` return V1 JSON and include the exact disclaimer.
- Dashboard: PASS — real browser QA showed the Federated Learning panel with disclaimer, 5 clients, 5 rounds, latest metrics, MLflow run id, and per-client summaries.
- ROS2/Nav2/SLAM freeze: PASS — no PR diff under ROS2/Nav2/SLAM paths; compose config commands still validate.

## Flower / FedAvg Evidence

Default 3-client run (`FL_SEED=42 make learning-fl-run`):

- Flower/Ray simulation started and logged real server warnings/info.
- `framework`: `flower==1.30.0`
- `strategy`: `FedAvg`
- `model_type`: `AxonFLModelV1`
- `model_param_count`: 850
- `global_loss`: 0.713159 -> 0.352060
- `global_accuracy`: 0.377778 -> 0.857778
- `mlflow_run_id`: present

5-client evidence run (`FL_NUM_CLIENTS=5 FL_SEED=42 make learning-fl-run`):

- `global_loss`: 0.710497 -> 0.269330
- `global_accuracy`: 0.394521 -> 0.945205
- `mlflow_run_id`: present
- `client_summaries`: 5 clients

## MLflow File-Based Evidence

- MLflow server was stopped with `docker compose stop mlflow 2>/dev/null || true`.
- `artifacts/mlops/mlruns/` was removed and recreated by `make learning-fl-run`.
- Latest run contains params (`num_clients`, `model_type`, `strategy`), metrics (`global_loss`, `global_accuracy`), and artifacts (`federated_report.json`, `client_distribution_summary.json`, `convergence.json`, `convergence.csv`, `model_card_axon_fl_v1.md`).
- No `http://localhost:5000` server was required.

## Synthetic Data Quality

`client_distribution_summary.json` shows distinct non-IID clients:

- `edge-client-01`: `emg_fatigue_noise`, high EMG variance/spike pattern.
- `edge-client-02`: `ecg_drift_spike`, ECG-like drift/spike pattern.
- `edge-client-03`: `imu_movement_dropout`, IMU movement/dropout pattern.
- `edge-client-04`: `spo2_low_missing`, elevated `spo2_missing_ratio`.
- `edge-client-05`: `mixed_multi_anomaly`, mixed multi-signal anomaly pattern.

No real patient data or clinical datasets are used.

## Reproducibility

- `FL_NUM_CLIENTS=5 FL_SEED=42 make learning-fl-run` run twice produced identical normalized reports after removing `experiment_id`, `timestamp_utc`, and `mlflow_run_id`.
- `FL_NUM_CLIENTS=5 FL_SEED=123 make learning-fl-run` produced different metrics/distributions.
- Seed 42 loss/accuracy: 0.710497 -> 0.269330; 0.394521 -> 0.945205.
- Seed 123 loss/accuracy: 0.674549 -> 0.560310; 0.630137 -> 0.676712.

## Evidence Artifacts

Runtime artifacts are regenerated on demand and gitignored:

- `artifacts/learning/federated/federated_report.json`
- `artifacts/learning/federated/client_distribution_summary.json`
- `artifacts/learning/federated/convergence.json`
- `artifacts/learning/federated/convergence.csv`
- `artifacts/learning/federated/model_card_axon_fl_v1.md`
- `artifacts/mlops/mlruns/`

Browser screenshot captured locally:

- `/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/phase-6a-dashboard-federated-panel-5-clients.png`

## Bugs Found And Fixed

- `make learning-fl-run` ignored `FL_SEED`, so the documented reproducibility commands with `FL_SEED=123` would still run seed 42. Fixed by reading `FL_SEED` from the environment.
- `make learning-fl-run` could not vary client count/rounds/epochs from the environment. Fixed by supporting `FL_NUM_CLIENTS`, `FL_NUM_ROUNDS`, and `FL_LOCAL_EPOCHS` while preserving defaults.
- `services/learning/Dockerfile` used an unquoted `torch>=2.2,<3.0` spec, which can be parsed by the shell as redirection. Fixed by quoting the requirement.
- The API container could not see host-generated FL artifacts after `make learning-fl-run`, so Docker core returned idle even after a run. Fixed by mounting `./artifacts` read-only at `/app/artifacts` for the API service.
- The MLflow UI container served correctly but stayed `unhealthy` because the healthcheck used `curl` inside an image that does not provide it. Fixed by switching the healthcheck to Python `urllib.request`.

## Remaining Risks

- Full repo `ruff check .` still fails on pre-existing non-Phase-6A issues in edge inference and ROS2/Nav2 files. These were not changed to preserve ROS2/Nav2/SLAM freeze.
- Flower 1.30 emits a deprecation warning for `start_simulation`; the PR intentionally uses stable Flower 1.x APIs and still runs real Flower/Ray FedAvg.
- Building the learning Docker image downloads large CPU torch/Ray/MLflow dependencies and can take several minutes on a clean machine.

## Merge Recommendation

Ready to merge after the pushed QA fixes pass CI.
