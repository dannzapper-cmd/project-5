"""Phase 6B RL micro-module API contracts (versioned V1 schemas).

These mirror the conventions used by ``FederatedStatusV1`` / ``NavSlamStateV1``:
versioned, Pydantic-validated response models consumed by the dashboard. The RL
panel reads these — it never hardcodes metrics. The core API imports ONLY these
schemas and a file-based reader; it never imports gymnasium / Stable-Baselines3
/ torch (dependency isolation, item 8 / 6B-5).

Synthetic RL operational policy. No real patient data. No medical decisions.
Human review required for high-risk actions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RLRunStatus = Literal["idle", "running", "completed", "failed"]

# Exact disclaimer string (single line so it is grep-verifiable verbatim).
DISCLAIMER = "Synthetic RL operational policy. No real patient data. No medical decisions. Human review required for high-risk actions."  # noqa: E501


class RewardCurvePointV1(BaseModel):
    """One point on the training reward curve."""

    schema_version: Literal["v1"] = "v1"
    timesteps: int
    mean_episode_reward: float


class RLPolicySummaryV1(BaseModel):
    """Compact summary of the latest trained policy for the dashboard."""

    schema_version: Literal["v1"] = "v1"
    env_name: str | None = None
    algorithm: str | None = None
    reward_version: str | None = None
    safety_mode: str | None = None
    observation_dim: int | None = None
    action_count: int | None = None
    baseline_reward: float | None = None
    trained_policy_reward: float | None = None
    mean_reward: float | None = None
    policy_improvement_ratio: float | None = None
    unsafe_action_rate: float | None = None
    hitl_suggestion_rate: float | None = None
    episode_length_mean: float | None = None


class RLRunSummaryV1(BaseModel):
    """Compact summary of the latest RL run (run metadata)."""

    schema_version: Literal["v1"] = "v1"
    experiment_id: str | None = None
    timestamp_utc: str | None = None
    seed: int | None = None
    env_name: str | None = None
    algorithm: str | None = None
    total_timesteps_or_episodes: int | None = None
    reward_version: str | None = None
    mlflow_run_id: str | None = None
    report_path: str | None = None


class RLStatusV1(BaseModel):
    """Status endpoint payload (valid before AND after a run)."""

    schema_version: Literal["v1"] = "v1"
    status: RLRunStatus = "idle"
    has_run: bool = False
    env_name: str | None = None
    algorithm: str | None = None
    baseline_reward: float | None = None
    trained_policy_reward: float | None = None
    mean_reward: float | None = None
    policy_improvement_ratio: float | None = None
    unsafe_action_rate: float | None = None
    hitl_suggestion_rate: float | None = None
    summary: RLRunSummaryV1 = Field(default_factory=RLRunSummaryV1)
    policy_summary: RLPolicySummaryV1 = Field(default_factory=RLPolicySummaryV1)
    mlflow_run_id: str | None = None
    report_path: str | None = None
    artifact_dir: str | None = None
    synthetic_only: bool = True
    disclaimer: str = DISCLAIMER


class RLResultV1(BaseModel):
    """Full latest-result payload including the training reward curve."""

    schema_version: Literal["v1"] = "v1"
    status: RLRunStatus = "idle"
    has_run: bool = False
    summary: RLRunSummaryV1 = Field(default_factory=RLRunSummaryV1)
    policy_summary: RLPolicySummaryV1 = Field(default_factory=RLPolicySummaryV1)
    reward_curve: list[RewardCurvePointV1] = Field(default_factory=list)
    observation_names: list[str] = Field(default_factory=list)
    action_names: list[str] = Field(default_factory=list)
    synthetic_only: bool = True
    disclaimer: str = DISCLAIMER
