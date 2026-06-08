# Phase 6B Local QA Report

> Synthetic RL operational policy. No real patient data. No medical decisions.
> Human review required for high-risk actions.

## Summary

- Branch: `cursor/phase-6b-rl-micro-module-6d36` (intended: `feat/phase-6b-rl-micro-module`)
- Scope: Phase 6B RL micro-module only. No Phase 7. No ROS2/Nav2/SLAM changes.
  No changes to Phase 6A federated learning.
- Verdict: PASS (Docker compose-config and browser steps to be confirmed in a
  Docker-capable local environment — Docker is unavailable in Cursor Web).

## Environment

- Python 3.12, CPU-only.
- `gymnasium==0.29.1`, `stable-baselines3==2.3.2`, `torch 2.x (CPU)`,
  `mlflow` (file store), `flwr==1.30.0` (Phase 6A, unchanged).

## Commands run (in Cursor Web)

```bash
# deps (isolated venv)
.venv/bin/pip install -e ".[dev,edge-ai,agents,mlops]"
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r requirements-learning.txt
.venv/bin/pip install gymnasium==0.29.1 stable-baselines3==2.3.2

# version + env checks
python -c "import gymnasium, stable_baselines3; print(gymnasium.__version__, stable_baselines3.__version__)"
python -c "from gymnasium.utils.env_checker import check_env; from apps.learning.rl.environment import AxonTriageEnvV1; check_env(AxonTriageEnvV1())"

# tests + lint + verify
RL_CI_MODE=true pytest tests/phase6b/ -q
pytest tests/                      # full suite
ruff check apps/learning/rl apps/api/app/.../rl* scripts/run_rl_micro_module.py tests/phase6b
bash scripts/verify_phase6b.sh

# real default runs + reproducibility
rm -rf artifacts/learning/rl artifacts/mlops/mlruns
python scripts/run_rl_micro_module.py --seed 42
python scripts/run_rl_micro_module.py --seed 42 --no-mlflow   # x2 for repro
python scripts/run_rl_micro_module.py --seed 123 --no-mlflow

# API import isolation
python -c "import sys; sys.modules['stable_baselines3']=None; sys.modules['gymnasium']=None; sys.modules['torch']=None; from apps.api.main import app; print('OK')"
```

## Results

- `gymnasium 0.29.1`, `stable_baselines3 2.3.2` — confirmed.
- `gymnasium.utils.env_checker.check_env(AxonTriageEnvV1())` — PASS.
- `RL_CI_MODE=true pytest tests/phase6b/` — PASS (46 tests, ~9s).
- `pytest tests/` (full suite) — PASS (193 passed).
- `ruff check` (Phase 6B scope) — PASS.
- `bash scripts/verify_phase6b.sh` — PASS (Docker steps SKIP: Docker unavailable
  in Cursor Web).
- FastAPI import isolation (no gymnasium/SB3/torch/flwr) — PASS.
- Dependency isolation: `gymnasium`/`stable-baselines3`/`torch` absent from
  `requirements.txt` and core `[project.dependencies]` — PASS.

## RL evidence (default run, 15000 timesteps, 100 eval episodes)

| Seed | baseline_reward | trained_policy_reward | improvement | unsafe_action_rate | hitl_suggestion_rate |
|------|-----------------|-----------------------|-------------|--------------------|----------------------|
| 42 | 0.540 | 75.419 | 138.7 | 0.000 | 0.324 |
| 123 | 0.955 | 75.579 | ~78 | 0.000 | 0.321 |

- Trained policy beats the random baseline by a wide margin (BLOCKER 6B-3 PASS).
- `unsafe_action_rate` < 0.30 (PASS); `hitl_suggestion_rate` in [0.05, 0.60]
  (PASS).
- `rl_report.json` contains all required schema fields, `env_name =
  AxonTriageEnvV1`, `reward_version = REWARD_V1`, exact disclaimer (PASS).
- MLflow run created locally under `axon_rl_micro_module`; `mlflow_run_id` not
  null; no server required (PASS).

## Reproducibility

- Two runs with `--seed 42` produced identical `rl_report.json` metrics after
  removing `experiment_id`, `timestamp_utc`, `mlflow_run_id` (PASS).
- `--seed 123` produced different metrics (PASS).

## Phase 6A protection

- Full test suite (incl. `tests/phase6a/`) passes.
- RL artifacts live under `artifacts/learning/rl/`; FL under
  `artifacts/learning/federated/` — no path collision (verified by grep).
- `rl-runner` coexists with `fl-runner` in the `learning` compose profile
  (validated by parsing `docker-compose.yml`).

## ROS2/Nav2/SLAM freeze

- `git diff --name-only main...HEAD -- ros2_ws/ robotics/ services/ros2-bridge/
  services/ros2-nav-slam-minilab/` — empty.

## Local QA to confirm in a Docker-capable environment

```bash
docker compose --profile core config            # expect: no gymnasium/SB3/torch/rl-runner
docker compose --profile learning config        # expect: rl-runner + fl-runner + mlflow
docker compose --profile core up -d && curl http://localhost:8000/health
curl http://localhost:8000/api/learning/rl/status
# open http://localhost:3000 -> RL Micro-module panel with exact disclaimer
```

## Notes / limitations

- Docker is not available in Cursor Web; compose `config` and browser checks are
  documented above for a local Docker-capable run. Compose structure was
  validated by parsing `docker-compose.yml` (rl-runner in learning/full only).
- PPO uses `ent_coef=0.03` and 15000 timesteps (above the 5000 floor) so the
  HITL suggestion rate stays in the required operational band across seeds.
