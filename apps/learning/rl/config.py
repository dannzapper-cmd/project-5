"""Phase 6B RL micro-module configuration, paths, and observation/action specs.

All values are deterministic and CPU-friendly. The RL experiment is on-demand
only; importing this module has no side effects beyond defining constants.

Synthetic RL operational policy. No real patient data. No medical decisions.
Human review required for high-risk actions.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root: apps/learning/rl/config.py -> parents[3] == repo root.
ROOT = Path(__file__).resolve().parents[3]

# Artifacts live alongside the Phase 6A federated artifacts but in their OWN
# subtree so the two modules never collide (RL != federated).
RL_ARTIFACTS = ROOT / "artifacts" / "learning" / "rl"
RUNS_DIR = RL_ARTIFACTS / "runs"
LATEST_REPORT_PATH = RL_ARTIFACTS / "rl_report.json"
STATUS_PATH = RL_ARTIFACTS / "status.json"
REWARD_CURVE_JSON_PATH = RL_ARTIFACTS / "reward_curve.json"
REWARD_CURVE_CSV_PATH = RL_ARTIFACTS / "reward_curve.csv"
POLICY_SUMMARY_PATH = RL_ARTIFACTS / "policy_summary.json"
SAFETY_ENVELOPE_PATH = RL_ARTIFACTS / "safety_envelope.md"
POLICY_MODEL_PATH = RL_ARTIFACTS / "policy_axon_triage_v1.zip"

# MLflow defaults to a local file store so no server is ever required (shared
# tracking dir with the rest of the project; the experiment name is distinct).
MLFLOW_DEFAULT_TRACKING_DIR = ROOT / "artifacts" / "mlops" / "mlruns"
MLFLOW_EXPERIMENT_NAME = os.getenv("RL_MLFLOW_EXPERIMENT", "axon_rl_micro_module")

# Reproducibility (item 13 of the Phase 6B guardrails).
DEFAULT_SEED = int(os.getenv("RL_SEED", "42"))

ENV_NAME = "AxonTriageEnvV1"
REWARD_VERSION = "REWARD_V1"
SAFETY_MODE = "synthetic_operational_triage_hitl_required"

# --- Observation contract (10 dims, fixed order) -------------------------
# Every feature is normalized to [0.0, 1.0]. The environment, the reward
# function, and the docs share this exact ordering.
OBSERVATION_NAMES: tuple[str, ...] = (
    "risk_score",                # 0: 0.0 = no risk, 1.0 = max risk
    "fusion_confidence",         # 1: 0.0 = no confidence, 1.0 = full confidence
    "anomaly_count_normalized",  # 2: 0.0 = 0 anomalies, 1.0 = 10+ anomalies
    "sensor_dropout_ratio",      # 3: 0.0 = all sensors ok, 1.0 = all sensors down
    "inference_latency_normalized",  # 4: 0.0 = 0ms, 1.0 = 500ms+
    "system_load_normalized",    # 5: 0.0 = idle, 1.0 = overloaded
    "alert_severity",            # 6: 0.0 = none, 1.0 = critical
    "robot_state_risk",          # 7: 0.0 = safe, 1.0 = unsafe
    "recent_false_positive_rate",  # 8: 0.0 = none, 1.0 = all false positives
    "human_review_required",     # 9: 0.0 = no, 1.0 = yes
)
OBSERVATION_DIM = len(OBSERVATION_NAMES)

# --- Action contract (6 discrete, safe operational actions) --------------
ACTION_NAMES: tuple[str, ...] = (
    "keep_normal",                    # 0: no change, normal priority
    "raise_alert",                    # 1: escalate alert priority
    "lower_alert",                    # 2: de-escalate alert priority
    "suggest_conservative_threshold",  # 3: recommend a conservative threshold
    "request_hitl",                   # 4: request human-in-the-loop review
    "allocate_resource",              # 5: allocate simulated resource to triage/safety
)
ACTION_COUNT = len(ACTION_NAMES)

# Episode length cap (item 6B-4).
MAX_EPISODE_STEPS = 200

# --- Hyperparameter profiles (item 6B-10) --------------------------------
# DEFAULT = the real portfolio run. CI/TEST = tiny, must finish < 30s/test.
DEFAULT_TOTAL_TIMESTEPS = int(os.getenv("RL_TOTAL_TIMESTEPS", "15000"))
DEFAULT_EVAL_EPISODES = int(os.getenv("RL_EVAL_EPISODES", "100"))

CI_TOTAL_TIMESTEPS = 500
CI_EVAL_EPISODES = 5

# Floor for the default portfolio run (version policy patch): never below 5000
# for the PPO path. Tests set RL_CI_MODE=true to use the tiny CI profile.
MIN_DEFAULT_TIMESTEPS = 5000


def ci_mode() -> bool:
    """True when RL_CI_MODE is set (tests use tiny timesteps/episodes)."""
    return os.getenv("RL_CI_MODE", "").lower() in {"1", "true", "yes"}


def resolved_timesteps(total_timesteps: int | None = None) -> int:
    """Resolve training timesteps honoring CI mode and the default floor."""
    if ci_mode():
        return CI_TOTAL_TIMESTEPS
    if total_timesteps is None:
        total_timesteps = DEFAULT_TOTAL_TIMESTEPS
    return max(MIN_DEFAULT_TIMESTEPS, int(total_timesteps))


def resolved_eval_episodes(eval_episodes: int | None = None) -> int:
    """Resolve evaluation episode count honoring CI mode."""
    if ci_mode():
        return CI_EVAL_EPISODES
    return int(eval_episodes if eval_episodes is not None else DEFAULT_EVAL_EPISODES)
