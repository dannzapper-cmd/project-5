# Phase 6B Local QA Report

> Synthetic RL operational policy. No real patient data. No medical decisions.
> Human review required for high-risk actions.

## Summary

- **Branch (local):** `feat/phase-6b-rl-micro-module` (tracking PR #11 head `cursor/phase-6b-rl-micro-module-6d36`)
- **Commit base:** `ec71a4c3177b5d87a92a2deee867cab98da7ef37`
- **QA host:** macOS darwin 25.5.0, Docker Desktop, Python 3.12.13 (.venv)
- **Verdict:** **PASS** — first real local Docker + API + dashboard validation; no code fixes required

## Evidence Manifest

| Check | Command | Result | Evidence Path / Output Snippet |
|---|---|---|---|
| Full tests | `make test` | PASS | `193 passed in 37.78s` |
| Phase 6B CI tests | `RL_CI_MODE=true pytest tests/phase6b/ -v` | PASS | `46 passed in 6.73s` |
| Verify script | `bash scripts/verify_phase6b.sh` | PASS | lint + smoke + compose config + isolation |
| RL full run | `RL_SEED=42 make learning-rl-run` | PASS | `artifacts/learning/rl/rl_report.json` |
| MLflow file-based | run with mlflow server stopped | PASS | experiment `axon_rl_micro_module` in `artifacts/mlops/mlruns` |
| Reproducibility | two runs `RL_SEED=42` | PASS | trained diff=0.0 |
| Docker core config | `docker compose --profile core config \| grep -Ei gymnasium\|torch` | PASS | `ISOLATION CLEAN` |
| Docker learning config | `docker compose --profile learning config` | PASS | rl-runner + fl-runner + mlflow |
| Docker core health | `curl http://localhost:8000/health` | PASS | `HTTP 200`, `"status":"ok"` |
| Docker learning | `docker compose --profile learning up -d` | PASS | rl-runner, fl-runner, mlflow started (1st attempt: stale network; retry OK) |
| API RL | `curl .../api/learning/rl/{status,latest,history}` | PASS | exact disclaimer, real metrics |
| Dashboard browser | `http://localhost:3000` | PASS | RL panel visible; disclaimer rendered verbatim |
| Fase 6A FL | `make learning-fl-run` + FL API | PASS | `final_global_accuracy: 0.857778` |
| ROS2 freeze | `git diff main...HEAD -- ros2_ws/` | PASS | empty diff |

## Environment

| Package | Version |
|---|---|
| gymnasium | 0.29.1 |
| stable-baselines3 | 2.3.2 |
| torch | 2.12.0 (CPU) |
| mlflow | file store at `artifacts/mlops/mlruns` |

## Commands Run (Local QA — 2026-06-08)

```bash
git checkout feat/phase-6b-rl-micro-module   # fetched from origin/cursor/phase-6b-rl-micro-module-6d36
make install && make learning-install && make learning-rl-install

# Gymnasium API + dynamics (PASO 4–6, CONSTRAINT ADD 1–3)
.venv/bin/python -c "from apps.learning.rl.environment import AxonTriageEnvV1; ..."

# Clean artifacts + full RL run
rm -rf artifacts/mlops/mlruns/
RL_SEED=42 make learning-rl-run
RL_SEED=123 make learning-rl-run

# Reproducibility
RL_SEED=42 make learning-rl-run  # x2 → metrics identical

# Tests
make test                                    # 193 passed
RL_CI_MODE=true pytest tests/phase6b/ -v     # 46 passed
bash scripts/verify_phase6b.sh               # all PASS incl. Docker config

# Docker
docker compose --profile core up --build -d
curl http://localhost:8000/health            # 200
docker compose --profile learning build rl-runner
docker compose --profile learning up -d

# API
curl http://localhost:8000/api/learning/rl/status
curl http://localhost:8000/api/learning/rl/latest
curl http://localhost:8000/api/learning/rl/history

# Fase 6A
make learning-fl-run
curl http://localhost:8000/api/learning/federated/status

# Isolation (PASO 27.3)
docker compose --profile core config 2>&1 | grep -Ei "stable.baselines|gymnasium|gym\b|torch" || echo ISOLATION CLEAN
```

## RL Evidence (default run: 15000 timesteps, 100 eval episodes)

**Report path:** `artifacts/learning/rl/rl_report.json`

| Seed | baseline_reward | trained_policy_reward | improvement % | unsafe_action_rate | hitl_suggestion_rate |
|------|-----------------|-----------------------|---------------|--------------------|----------------------|
| 42 | 0.540 | 75.419 | 13866.5% | 0.000 | 0.324 |
| 123 | 0.955 | 75.579 | 7814.0% | 0.000 | 0.321 |

Gate criteria (PASO 23):

- trained > baseline: **PASS**
- improvement > 10%: **PASS** (13866.5%)
- unsafe_action_rate < 0.30: **PASS** (0.0)
- hitl_suggestion_rate ∈ [0.05, 0.60]: **PASS** (0.324)
- disclaimer exact: **PASS**

## MLflow (file-based, no server)

- Server stopped: `docker compose stop mlflow`
- Run succeeded; `mlflow_run_id` not null (e.g. `020fd605b7154120ae705221caa5c16b`)
- Experiment name: **`axon_rl_micro_module`** — verified via `mlflow.search_experiments()`

## Reproducibility

Two consecutive `RL_SEED=42 make learning-rl-run`:

```
baseline_reward: A=0.54 B=0.54 diff=0.0
trained_policy_reward: A=75.419 B=75.419 diff=0.0
unsafe_action_rate: A=0.0 B=0.0 diff=0.0
hitl_suggestion_rate: A=0.323639 B=0.323639 diff=0.0
```

Different seed (123) produces different baseline (0.955) — **PASS**.

## Docker

### Core profile

- `docker compose --profile core config` — PASS
- `docker compose --profile core up --build -d` — all services healthy
- `/health` → `200 {"status":"ok","service":"axon-api",...}`
- No gymnasium/SB3/torch in core config grep — **ISOLATION CLEAN**

### Learning profile

- `rl-runner` image built (`axon-rl-runner`)
- `fl-runner`, `rl-runner`, `mlflow` coexist
- Both runners are one-shot (`restart: "no"`)
- Note: first `learning up` hit stale Docker network (`network ... not found`); `learning down && up` resolved it

## API Endpoints

All three RL endpoints return valid JSON with exact disclaimer:

```
disclaimer: Synthetic RL operational policy. No real patient data. No medical decisions. Human review required for high-risk actions.
baseline: 0.54
trained: 75.419
unsafe: 0.0
hitl: 0.323639
env: AxonTriageEnvV1
algo: PPO (Stable-Baselines3)
```

FastAPI import isolation (SB3/gymnasium/torch blocked) — **OK**.

## Dashboard (browser QA)

- URL: `http://localhost:3000`
- **RL Micro-module Phase 6B** panel visible
- Disclaimer rendered verbatim (accessibility snapshot ref: exact  sentence match)
- Panel polls `/api/learning/rl/status` — shows live metrics after load
- Report path displayed: `/app/artifacts/learning/rl/rl_report.json`

## Phase 6A Protection

- `make learning-fl-run` — PASS (`final_global_accuracy: 0.857778`)
- FL API `/api/learning/federated/status` — PASS, separate artifact path
- No `federated_report` in `apps/learning/rl/`; no `rl_report` in `apps/learning/federated/`

## ROS2/Nav2/SLAM Freeze

- `git diff main...HEAD -- ros2_ws/ robotics/` — **empty**
- `verify_phase6b.sh` ROS2 check — **PASS**

## verify_phase6b.sh Assessment

Script validates **behavior**, not just file existence: lint, CI-mode pytest, smoke run (500 timesteps), report schema, dependency isolation, FastAPI import isolation, Docker compose profiles, safety grep, disclaimer grep, FL artifact isolation, ROS2 freeze.

## Bugs Found

1. **Transient Docker network error** on first `docker compose --profile learning up` (`network ... not found`). Resolved by `learning down && up`. Not a code bug.
2. **Cursor Web QA report** (prior) marked Docker/browser as SKIP — superseded by this local run.

## Fixes Applied

None — all gates passed without code changes.

## Remaining Risks

- Docker learning profile may fail on stale networks after abrupt `core down`; retry `learning down && up`.
- `rl-runner` in Docker uses CI-mode defaults unless env overrides set — API may briefly show CI smoke metrics until full run completes.
- Dashboard RL metrics depend on API polling (10s interval); initial load may show idle state for ~1 poll cycle.

## Merge Recommendation

**Ready to merge** — all 15 gate criteria PASS; first real local Docker validation complete.

---

## Self-Review Results (Paso 27)

### Self-Rating Total: 58/60

| Área | Rating | Nota |
|---|---|---|
| Gymnasium env dynamics | 5/5 | HITL action clears obs[9]; risk_score dynamic |
| Reward design completeness | 5/5 | REWARD_V1 fully documented in reward.py |
| RL convergence real | 5/5 | trained 75.419 >> baseline 0.54 |
| Dependency isolation | 5/5 | core config grep clean |
| MLflow file-based | 5/5 | works with server stopped |
| Test quality | 5/5 | RL_CI_MODE, 46 tests in ~7s |
| Dashboard disclaimer | 5/5 | exact text rendered in browser |
| Reproducibility | 5/5 | seed 42 → identical metrics |
| Fase 6A protection | 5/5 | FL run + API intact |
| ROS2/Nav2/SLAM freeze | 5/5 | no diff |
| ADR-012 completeness | 5/5 | Status/Context/Decision/Consequences/Not Doing |
| Evidence quality | 4/5 | full local run; Docker network glitch documented |

### Critical Findings from Self-Audit

- (a) `AxonTriageEnvV1.step()` modifies state based on action — **PASS** (HITL clears human_review_required)
- (b) Reward uses REWARD_V1 constants — **PASS**
- (c) Baseline is random policy, same eval episodes/seed — **PASS**
- (d) Backend RL imports are lazy (rl_service reads files only) — **PASS**
- (e) Tests use RL_CI_MODE with 500 timesteps — **PASS**
- (f) ADR-012 has 4 substantive sections — **PASS**
- (g) Disclaimer in dashboard HTML + Pydantic schema — **PASS**
- (h) RL artifacts at `artifacts/learning/rl/`, FL at `artifacts/learning/federated/` — **PASS**, no collision

### Gate Checklist Result

**10/10** items passing.

Verdict: **PASS**

### Senior Improvements Identified (Not Blocking)

- [NICE-TO-HAVE] Add `docker compose learning` healthcheck wrapper to auto-recover stale networks.
- [TECH-DEBT] Dashboard initial idle flash before first RL poll — consider immediate fetch on panel mount.
- [FUTURE-FASE] Multi-seed evaluation dashboard chart (Phase 7 observability scope).
