"""MLflow logging for the RL micro-module (local file store by default).

MLflow logging must work WITHOUT a running MLflow server (item 6). We default to
a local ``file:`` tracking URI so ``mlflow ui`` is optional. If MLflow is not
installed, logging degrades gracefully and returns ``None`` (the experiment and
its JSON artifacts are still produced).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from apps.learning.rl.config import (
    MLFLOW_DEFAULT_TRACKING_DIR,
    MLFLOW_EXPERIMENT_NAME,
)


def default_tracking_uri() -> str:
    """Local file-based tracking URI (no server required)."""
    uri = os.getenv("MLFLOW_TRACKING_URI")
    if uri:
        return uri
    MLFLOW_DEFAULT_TRACKING_DIR.mkdir(parents=True, exist_ok=True)
    return MLFLOW_DEFAULT_TRACKING_DIR.resolve().as_uri()


def log_rl_run(report: dict[str, Any], artifacts: list[Path]) -> str | None:
    """Log params/metrics/artifacts for an RL run. Returns the run id or None."""
    try:
        import mlflow
    except ImportError:
        return None

    mlflow.set_tracking_uri(default_tracking_uri())
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run() as run:
        mlflow.log_params(
            {
                "env_name": report["env_name"],
                "algorithm": report["algorithm"],
                "seed": report["seed"],
                "total_timesteps_or_episodes": report["total_timesteps_or_episodes"],
                "reward_version": report["reward_version"],
                "observation_dim": report["observation_dim"],
                "action_count": report["action_count"],
                "safety_mode": report["safety_mode"],
            }
        )
        mlflow.log_metric("mean_reward", float(report["mean_reward"]))
        mlflow.log_metric("final_eval_reward", float(report["final_eval_reward"]))
        mlflow.log_metric("baseline_reward", float(report["baseline_reward"]))
        mlflow.log_metric("trained_policy_reward", float(report["trained_policy_reward"]))
        mlflow.log_metric("unsafe_action_rate", float(report["unsafe_action_rate"]))
        mlflow.log_metric("hitl_suggestion_rate", float(report["hitl_suggestion_rate"]))
        mlflow.log_metric("episode_length_mean", float(report["episode_length_mean"]))
        mlflow.log_metric(
            "policy_improvement_ratio", float(report["policy_improvement_ratio"])
        )
        for entry in report.get("reward_curve", []):
            mlflow.log_metric(
                "reward_curve_mean_episode_reward",
                float(entry["mean_episode_reward"]),
                step=int(entry["timesteps"]),
            )
        for path in artifacts:
            if path.exists():
                mlflow.log_artifact(str(path))
        return run.info.run_id
