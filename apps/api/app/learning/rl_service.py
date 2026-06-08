"""Read the latest RL run artifacts and build versioned API payloads.

The status endpoint must work before any run (idle, null metrics, disclaimer
present) and after a run (completed, populated metrics). All reads are defensive:
missing/corrupt files degrade to a safe idle state.

IMPORTANT (dependency isolation): this module imports ONLY lightweight path
constants from ``apps.learning.rl.config`` (no gymnasium / Stable-Baselines3 /
torch). The core API stays lightweight and importable without learning deps.

Synthetic RL operational policy. No real patient data. No medical decisions.
Human review required for high-risk actions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.api.app.schemas.rl import (
    RewardCurvePointV1,
    RLPolicySummaryV1,
    RLResultV1,
    RLRunSummaryV1,
    RLStatusV1,
)
from apps.learning.rl.config import (
    LATEST_REPORT_PATH,
    RL_ARTIFACTS,
    STATUS_PATH,
)


def _safe_read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _policy_summary(report: dict) -> RLPolicySummaryV1:
    return RLPolicySummaryV1(
        env_name=report.get("env_name"),
        algorithm=report.get("algorithm"),
        reward_version=report.get("reward_version"),
        safety_mode=report.get("safety_mode"),
        observation_dim=report.get("observation_dim"),
        action_count=report.get("action_count"),
        baseline_reward=report.get("baseline_reward"),
        trained_policy_reward=report.get("trained_policy_reward"),
        mean_reward=report.get("mean_reward"),
        policy_improvement_ratio=report.get("policy_improvement_ratio"),
        unsafe_action_rate=report.get("unsafe_action_rate"),
        hitl_suggestion_rate=report.get("hitl_suggestion_rate"),
        episode_length_mean=report.get("episode_length_mean"),
    )


def _summary(report: dict) -> RLRunSummaryV1:
    return RLRunSummaryV1(
        experiment_id=report.get("experiment_id"),
        timestamp_utc=report.get("timestamp_utc"),
        seed=report.get("seed"),
        env_name=report.get("env_name"),
        algorithm=report.get("algorithm"),
        total_timesteps_or_episodes=report.get("total_timesteps_or_episodes"),
        reward_version=report.get("reward_version"),
        mlflow_run_id=report.get("mlflow_run_id"),
        report_path=str(LATEST_REPORT_PATH),
    )


def _reward_curve(report: dict) -> list[RewardCurvePointV1]:
    return [
        RewardCurvePointV1(
            timesteps=int(p["timesteps"]),
            mean_episode_reward=float(p["mean_episode_reward"]),
        )
        for p in report.get("reward_curve", [])
    ]


def _resolve_status(report: dict | None, status_doc: dict | None) -> str:
    if status_doc and status_doc.get("status"):
        return str(status_doc["status"])
    return "completed" if report else "idle"


def get_rl_status() -> RLStatusV1:
    """Build the RLStatusV1 payload (idle when no run exists)."""
    report = _safe_read_json(LATEST_REPORT_PATH)
    status_doc = _safe_read_json(STATUS_PATH)
    status = _resolve_status(report, status_doc)

    if report is None:
        return RLStatusV1(
            status=status,  # type: ignore[arg-type]
            has_run=False,
            artifact_dir=str(RL_ARTIFACTS),
        )

    return RLStatusV1(
        status=status,  # type: ignore[arg-type]
        has_run=True,
        env_name=report.get("env_name"),
        algorithm=report.get("algorithm"),
        baseline_reward=report.get("baseline_reward"),
        trained_policy_reward=report.get("trained_policy_reward"),
        mean_reward=report.get("mean_reward"),
        policy_improvement_ratio=report.get("policy_improvement_ratio"),
        unsafe_action_rate=report.get("unsafe_action_rate"),
        hitl_suggestion_rate=report.get("hitl_suggestion_rate"),
        summary=_summary(report),
        policy_summary=_policy_summary(report),
        mlflow_run_id=report.get("mlflow_run_id"),
        report_path=str(LATEST_REPORT_PATH),
        artifact_dir=str(RL_ARTIFACTS),
    )


def get_rl_result() -> RLResultV1:
    """Build the full RLResultV1 payload (idle when no run exists)."""
    report = _safe_read_json(LATEST_REPORT_PATH)
    status_doc = _safe_read_json(STATUS_PATH)
    status = _resolve_status(report, status_doc)

    if report is None:
        return RLResultV1(status=status, has_run=False)  # type: ignore[arg-type]

    return RLResultV1(
        status=status,  # type: ignore[arg-type]
        has_run=True,
        summary=_summary(report),
        policy_summary=_policy_summary(report),
        reward_curve=_reward_curve(report),
        observation_names=report.get("observation_names", []),
        action_names=report.get("action_names", []),
    )


def get_rl_history(limit: int = 20) -> dict[str, Any]:
    """Lightweight history view from the per-run artifacts directory."""
    runs_dir = RL_ARTIFACTS / "runs"
    runs: list[dict] = []
    if runs_dir.exists():
        for path in sorted(runs_dir.glob("*.json"), reverse=True)[:limit]:
            doc = _safe_read_json(path)
            if doc:
                runs.append(
                    {
                        "experiment_id": doc.get("experiment_id"),
                        "timestamp_utc": doc.get("timestamp_utc"),
                        "baseline_reward": doc.get("baseline_reward"),
                        "trained_policy_reward": doc.get("trained_policy_reward"),
                        "policy_improvement_ratio": doc.get("policy_improvement_ratio"),
                        "mlflow_run_id": doc.get("mlflow_run_id"),
                    }
                )
    return {"runs": runs, "synthetic_only": True}
