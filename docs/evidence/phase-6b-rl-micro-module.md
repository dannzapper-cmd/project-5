# Phase 6B — RL Micro-module (synthetic safe operational triage policy)

> **Synthetic RL operational policy. No real patient data. No medical decisions.
> Human review required for high-risk actions.**
>
> This reinforcement learning module only optimizes synthetic *operational*
> triage suggestions. It does not diagnose, treat, or recommend clinical actions,
> does not control real hardware or robots, and never takes irreversible or
> safety-critical actions. Trained and evaluated on synthetic data only.

## Overview

Phase 6B adds a tiny, reproducible **reinforcement learning** micro-module to
AXON. A small Gymnasium environment (`AxonTriageEnvV1`) simulates safe
operational decision-making — alert prioritization, conservative threshold
suggestions, simulated resource allocation, and human-in-the-loop (HITL)
escalation. A short PPO training run (Stable-Baselines3) learns a policy that
clearly beats a random baseline. Everything is CPU-only, fixed-seed, local-first,
on-demand, and logged to a local file-based MLflow store.

Phase 6B does **not** implement Phase 7, does **not** modify ROS2/Nav2/SLAM, and
does **not** change Phase 6A federated learning.

## Environment: `AxonTriageEnvV1`

- **Gymnasium (Farama) `0.29.1`** — `reset()` returns `(obs, info)`, `step()`
  returns `(obs, reward, terminated, truncated, info)`. Not legacy `gym`.
- **Observation:** `Box(low=0.0, high=1.0, shape=(10,), dtype=float32)`, fixed
  order: `risk_score, fusion_confidence, anomaly_count_normalized,
  sensor_dropout_ratio, inference_latency_normalized, system_load_normalized,
  alert_severity, robot_state_risk, recent_false_positive_rate,
  human_review_required`.
- **Action:** `Discrete(6)`: `0 keep_normal, 1 raise_alert, 2 lower_alert,
  3 suggest_conservative_threshold, 4 request_hitl, 5 allocate_resource`.
- **Dynamics (real transitions, not static):** `risk_score` is a dynamic state
  variable — `raise_alert` propagates it upward, `request_hitl` eases it and
  clears the human-review flag, and `keep_normal` on an already-high risk lets it
  climb (never decreases it). Exogenous contextual features are resampled each
  step with controlled Gaussian noise (`N(0, 0.05)`). Episodes run up to 200
  steps; they terminate early when `risk_score` reaches 1.0.

## Reward: `REWARD_V1`

Small, bounded, fully documented constants (`apps/learning/rl/reward.py`):

| Condition | Reward |
|-----------|--------|
| `raise_alert` and `risk_score > 0.7` | +1.5 |
| `request_hitl` and (`risk_score > 0.6` or `fusion_confidence < 0.4`) | +1.0 |
| `suggest_conservative_threshold` and `sensor_dropout_ratio > 0.5` | +0.5 |
| `keep_normal` and `risk_score < 0.3` | +0.3 |
| `keep_normal` and `risk_score > 0.7` | −1.0 |
| `raise_alert` and `risk_score < 0.2` | −0.8 |
| `lower_alert` and `risk_score > 0.6` | −0.5 |
| `allocate_resource` and `system_load < 0.2` | −1.5 |
| `request_hitl` and `risk_score < 0.6` and `fusion_confidence >= 0.4` | −0.5 |
| any action and `inference_latency_normalized > 0.8` | −0.2 |

The last penalty (unnecessary HITL) is a documented addition to the base spec:
without it the optimal policy degenerates to *always* requesting human review
(HITL rate 1.0). It mirrors the "don't escalate everything to a human"
principle and keeps the HITL suggestion rate in a realistic operational band.

## Algorithm

- **Stable-Baselines3 `2.3.2` PPO** (`MlpPolicy`, `net_arch=[64,64]`,
  `ent_coef=0.03`, `n_steps=512`, `n_epochs=6`), CPU-only, fixed seed.
- **Baseline:** a random policy (`action_space.sample()`) evaluated on the same
  episodes/seed as the trained policy, so the comparison is fair.
- No fallback was needed: SB3 installed cleanly alongside the existing learning
  `torch` pin. (A tabular-Q-learning fallback is documented in the ADR in case
  SB3 ever conflicts.)

## Safety envelope

- The RL policy only optimizes synthetic operational triage / suggestions.
- It does **not** make medical decisions, diagnose, treat, or recommend clinical
  actions.
- It does **not** control real hardware or robots and takes no irreversible /
  safety-critical actions.
- Human review is required for high-risk (`risk_score > 0.6`) or low-confidence
  (`fusion_confidence < 0.4`) situations; `request_hitl` exists for exactly this.

A `safety_envelope.md` artifact is regenerated with each run.

## How to reproduce locally

```bash
# 1) Install RL deps (isolated from core; CPU torch + Gymnasium + SB3 + MLflow)
make learning-rl-install
#    equivalently:
#    pip install torch --index-url https://download.pytorch.org/whl/cpu
#    pip install -r requirements-rl.txt

# 2) Run the RL experiment (default seed 42, 15000 timesteps, 100 eval episodes)
make learning-rl-run
#    or:  python scripts/run_rl_micro_module.py --seed 42

# 3) Inspect the report
make learning-rl-report

# 4) Manually review the learned policy (state -> action table)
make learning-rl-eval

# 5) API status (with the core API running)
make rl-status
#    curl http://localhost:8000/api/learning/rl/status
```

## Example evidence (seed 42, 15000 timesteps, 100 eval episodes)

| Metric | Value |
|--------|-------|
| baseline_reward (random policy) | 0.540 |
| trained_policy_reward (PPO) | 75.419 |
| policy_improvement_ratio | 138.7 |
| unsafe_action_rate | 0.000 |
| hitl_suggestion_rate | 0.324 |
| episode_length_mean (trained) | 165.7 |
| episode_length_mean (baseline) | 28.7 |

Seed 123 (for contrast): baseline 0.955, trained 75.579, HITL 0.321, unsafe
0.000. Two runs with the same seed produce identical report metrics (except
`experiment_id`, `timestamp_utc`, `mlflow_run_id`); different seeds differ.

Training reward curve (mean episode reward over rollouts) rises monotonically,
e.g. `512→0.98, 1024→1.54, 1536→3.39, 2048→5.31, 4096→8.66, …` and keeps
climbing through 15000 timesteps. The trained policy both **survives longer**
(episode length 165 vs the random baseline's 29) and accumulates far more
reward. (Exact values are reproducible for a fixed seed; timestamps differ.)

## Artifacts

Written to `artifacts/learning/rl/` (runtime outputs are gitignored):

- `rl_report.json` — full run report (schema below)
- `reward_curve.json` / `reward_curve.csv` — training reward curve
- `policy_summary.json` — compact policy summary
- `safety_envelope.md` — safety boundary + latest measured behavior
- `policy_axon_triage_v1.zip` — small trained SB3 policy (best-effort)
- `status.json` — idle/running/completed/failed marker
- `runs/<experiment_id>.json` — archived per-run reports (for `/history`)

MLflow run logged to `artifacts/mlops/mlruns/` under experiment
`axon_rl_micro_module` (params, metrics, and the artifacts above).

### `rl_report.json` schema (required fields)

`experiment_id`, `timestamp_utc`, `seed`, `env_name` (`"AxonTriageEnvV1"`),
`algorithm`, `total_timesteps_or_episodes`, `observation_dim` (10),
`action_count` (6), `reward_version` (`"REWARD_V1"`), `baseline_reward`,
`trained_policy_reward`, `mean_reward`, `unsafe_action_rate`,
`hitl_suggestion_rate`, `mlflow_run_id` (string or null), `disclaimer`.

## Dashboard

The dashboard renders an **RL Micro-module** panel showing run status,
environment name, algorithm, mean reward, baseline-vs-trained reward, policy
improvement ratio, unsafe-action rate, HITL suggestion rate, MLflow run id,
report path, and the training reward curve. The disclaimer *"Synthetic RL
operational policy. No real patient data. No medical decisions. Human review
required for high-risk actions."* is always visible (even before any run) and is
read from the API — never hardcoded.

## API

- `GET /api/learning/rl/status` — compact status (`RLStatusV1`), valid before
  (idle) and after (completed) a run.
- `GET /api/learning/rl/latest` — full latest result (`RLResultV1`) with the
  reward curve and observation/action names.
- `GET /api/learning/rl/history` — recent run summaries.

The core API imports only the V1 schemas and a file-based reader; it never
imports Gymnasium / Stable-Baselines3 / torch.

## Docker / profiles

- `docker compose --profile core config` — Gymnasium/SB3/torch absent (isolation).
- `docker compose --profile learning config` — `rl-runner` (one-shot) coexists
  with the Phase 6A `fl-runner` and `mlflow`.
- The RL experiment is triggered manually; it never auto-starts with core. The
  one-shot `rl-runner` trains once on demand (CPU, < 1 min).

## Expected tests

```bash
RL_CI_MODE=true pytest tests/phase6b/   # RL tests (skip if Gymnasium/SB3 absent)
bash scripts/verify_phase6b.sh          # lint + tests + smoke + schema + isolation + safety + freeze
```

## Known limitations

- The RL problem is intentionally narrow (operational triage suggestions only);
  it is a portfolio demonstration, not a production decision system.
- PPO needs `ent_coef=0.03` and ~15000 timesteps to reliably discover the HITL
  region; fewer timesteps can collapse the HITL suggestion rate.
- The random baseline ends episodes quickly (risk climbs unmanaged), so the
  improvement ratio is large — this is honest, not inflated.

## Scope boundaries

No Phase 7. No medical/clinical decisions. No real patient data. No real hardware
or robot control. No irreversible/safety-critical actions. No giant models. No
cloud dependency. No ROS2/Nav2/SLAM changes. No changes to Phase 6A FL.
