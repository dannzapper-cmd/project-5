# ADR-012: Phase 6B — RL Micro-module (synthetic safe operational triage policy)

## Status

Accepted

## Context

Phase 6 introduces AXON's learning layer. Phase 6A delivered the **federated
learning** half; Phase 6B delivers a small **reinforcement learning**
micro-module — the second, and final, half of Phase 6. AXON is a local-first,
evidence-driven, *synthetic* portfolio project for Simulated Rehab Robot Ops.

The operational problem this RL module explores is narrow and deliberately safe:
given a synthetic operational state (risk, fusion confidence, anomaly count,
sensor dropout, inference latency, system load, alert severity, robot-state risk,
recent false-positive rate, and a human-review flag), what is a good *operational
triage suggestion* — keep/raise/lower an alert's priority, suggest a conservative
threshold, request human-in-the-loop (HITL) review, or allocate a simulated
resource? This is an alert-prioritization / escalation problem, **not** a
clinical, diagnostic, or hardware-control problem. Phase 6B follows Phase 6A
because both belong to the learning layer and share the on-demand `learning`
Docker profile, the local file-based MLflow store, and the evidence-driven
dashboard/API conventions; keeping them in the same profile avoids a new
always-on service.

## Decision

- **Environment: Gymnasium (Farama) `gymnasium==0.29.1`, class `AxonTriageEnvV1`.**
  A 10-dim `Box(0,1)` observation space and a `Discrete(6)` action space, both
  with fixed, documented orderings. We use the Gymnasium API (`reset()` returns
  `(obs, info)`, `step()` returns `(obs, reward, terminated, truncated, info)`),
  **not** legacy `gym`. `risk_score` is a genuinely dynamic state variable that
  responds to actions (escalation propagates it, HITL eases it, ignoring a high
  risk lets it climb), so actions have real consequences — it is not a static
  observation generator.
- **Algorithm: Stable-Baselines3 `stable-baselines3==2.3.2` PPO** (`MlpPolicy`,
  `net_arch=[64,64]`, `ent_coef=0.03`), CPU-only, fixed seed. SB3 installed
  cleanly alongside the existing learning `torch>=2.2,<3.0` pin, so the
  documented tabular-Q-learning fallback was **not** needed. The entropy
  coefficient is required so PPO discovers the HITL region instead of collapsing
  to a single safe action.
- **Baseline: a random policy** (`action_space.sample()`) evaluated on the
  **same** episodes/seed as the trained policy, so the comparison is fair. The
  trained policy must beat the baseline for the PR to be acceptable.
- **Reward: `REWARD_V1`** — small, bounded, fully documented constants (see
  `apps/learning/rl/reward.py`). Positive for correctly escalating high risk,
  requesting HITL when risk is high / confidence is low, being conservative under
  degraded sensors, and not over-escalating low-risk noise; negative for ignoring
  high risk, escalating low-risk noise, de-escalating real risk, wasting
  resources, unnecessary HITL escalation, and simulated latency cost. No
  arbitrary 100× scales; the reported numbers are interpretable.
- **Reproducibility.** Seeds (`random`, `numpy`, `torch`, Gymnasium, SB3) are set
  before training/evaluation; default `RL_SEED=42`. Two runs with the same seed
  produce identical report metrics (except timestamps / experiment id / MLflow
  run id); a different seed produces different metrics.
- **MLflow logs to a local `file:` store by default** (experiment
  `axon_rl_micro_module`) — no server required.
- **On-demand learning profile.** Triggered manually (CLI / Makefile / one-shot
  `rl-runner` container). It never auto-starts with the API/core. Gymnasium / SB3
  / torch are isolated to `requirements-rl.txt` / the `rl` extra and the
  `learning` Docker profile; the core API never imports them.
- **Default run uses 15,000 timesteps** (above the documented 5,000 floor). The
  originally suggested 10,000 did not reliably keep the HITL suggestion rate in
  the required operational band across seeds; 15,000 does, while still training
  in well under a minute on CPU. Tests use the tiny CI profile
  (`RL_CI_MODE=true`, 500 timesteps).

## Consequences

- AXON gains a demonstrable, reproducible RL micro-module: a trained PPO policy
  that clearly beats a random baseline (default run: trained ≈ 75–80 vs baseline
  ≈ 1, HITL suggestion rate ≈ 0.32–0.34, unsafe-action rate ≈ 0.0), with
  `rl_report.json`, a reward curve, a policy summary, a safety envelope, and a
  local MLflow run. The dashboard `RL Micro-module` panel and
  `/api/learning/rl/*` endpoints read these artifacts live — never hardcoded.
- It does **not** solve clinical RL, does not generalize to production without a
  full HITL workflow, and is not a control system. It is a portfolio-grade
  demonstration of safe operational RL on synthetic data.
- CI stays light: RL-engine tests skip when Gymnasium/SB3 are absent and use the
  tiny CI profile when present; the API/safety/isolation tests run in core CI.

## Not Doing (Scope Boundaries)

- **No Phase 7** observability expansion in this PR.
- **No medical/clinical RL.** The policy never performs diagnosis, treatment, or
  clinical recommendations; the action space contains only safe operational
  suggestions.
- **No real hardware/robot control.** No `rclpy`, no ROS2/Nav2/SLAM changes, no
  physical or irreversible actions, no autonomous safety-critical actions.
- **No real patient data**, no clinical datasets — synthetic only.
- **No giant models** (tiny CPU MLP policy), no cloud dependency, no always-on
  training service.
- **No changes to Phase 6A federated learning** beyond living side-by-side in the
  `learning` profile (separate artifact paths, no shared mutable state).
