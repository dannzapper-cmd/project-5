"""Run the RL micro-module experiment and build the ``rl_report.json`` dict.

Pipeline (CPU-only, fixed-seed):
  1. Evaluate a RANDOM baseline policy over N episodes (item 6B-6).
  2. Train a short PPO policy on AxonTriageEnvV1.
  3. Evaluate the trained policy over the SAME N episodes.
  4. Assemble a schema-complete report (item 7 / 6B-4) comparing the two.

No artifacts are written here (see :mod:`apps.learning.rl.runner`). Synthetic RL
operational policy. No real patient data. No medical decisions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from apps.learning.rl.config import (
    ACTION_COUNT,
    ACTION_NAMES,
    ENV_NAME,
    OBSERVATION_DIM,
    OBSERVATION_NAMES,
    REWARD_VERSION,
    SAFETY_MODE,
    resolved_eval_episodes,
    resolved_timesteps,
)
from apps.learning.rl.disclaimer import DISCLAIMER
from apps.learning.rl.policy import (
    ALGORITHM,
    EvalMetrics,
    evaluate_baseline,
    evaluate_policy,
    train_ppo,
    trained_action_fn,
)


def _improvement_ratio(trained: float, baseline: float) -> float:
    denom = abs(baseline) if abs(baseline) > 1e-9 else 1.0
    return (trained - baseline) / denom


def run_rl_experiment(
    *,
    seed: int = 42,
    total_timesteps: int | None = None,
    eval_episodes: int | None = None,
) -> dict[str, Any]:
    """Train + evaluate the triage policy; return the full report dict.

    Returns the trained model under ``report["_model"]`` (popped by the runner
    before serialization) so the policy artifact can be saved if desired.
    """
    timesteps = resolved_timesteps(total_timesteps)
    n_eval = resolved_eval_episodes(eval_episodes)

    baseline: EvalMetrics = evaluate_baseline(n_episodes=n_eval, seed=seed)

    train_result = train_ppo(total_timesteps=timesteps, seed=seed)
    trained: EvalMetrics = evaluate_policy(
        trained_action_fn(train_result.model), n_episodes=n_eval, seed=seed
    )

    improvement = _improvement_ratio(trained.mean_reward, baseline.mean_reward)

    report: dict[str, Any] = {
        "experiment_id": f"rl-{uuid4().hex[:12]}",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "seed": int(seed),
        "env_name": ENV_NAME,
        "algorithm": ALGORITHM,
        "total_timesteps_or_episodes": int(timesteps),
        "observation_dim": int(OBSERVATION_DIM),
        "observation_names": list(OBSERVATION_NAMES),
        "action_count": int(ACTION_COUNT),
        "action_names": list(ACTION_NAMES),
        "reward_version": REWARD_VERSION,
        "safety_mode": SAFETY_MODE,
        "eval_episodes": int(n_eval),
        "baseline_reward": round(float(baseline.mean_reward), 6),
        "trained_policy_reward": round(float(trained.mean_reward), 6),
        "mean_reward": round(float(trained.mean_reward), 6),
        "final_eval_reward": round(float(trained.mean_reward), 6),
        "policy_improvement_ratio": round(float(improvement), 6),
        "unsafe_action_rate": round(float(trained.unsafe_action_rate), 6),
        "hitl_suggestion_rate": round(float(trained.hitl_suggestion_rate), 6),
        "episode_length_mean": round(float(trained.episode_length_mean), 6),
        "baseline_metrics": baseline.as_dict(),
        "trained_metrics": trained.as_dict(),
        "reward_curve": train_result.reward_curve,
        "mlflow_run_id": None,
        "synthetic_only": True,
        "disclaimer": DISCLAIMER,
        "_model": train_result.model,
    }
    return report
