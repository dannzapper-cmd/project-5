"""REWARD_V1 — transparent reward function for AxonTriageEnvV1 (Phase 6B).

The reward is intentionally small, bounded, and fully documented so the learned
policy and the reported numbers are interpretable (no arbitrary 100x scales, no
fabricated metrics). It rewards *safe operational triage* and penalizes clearly
inappropriate or wasteful actions. It NEVER rewards anything resembling medical,
clinical, or hardware-control behavior — the action space itself only contains
safe operational suggestions.

Reward shape (per step, summed):

  +1.5  raise_alert when risk_score > 0.7            (correctly escalated high risk)
  +1.0  request_hitl when risk_score > 0.6 OR
        fusion_confidence < 0.4                       (correctly asked for human review)
  +0.5  suggest_conservative_threshold when
        sensor_dropout_ratio > 0.5                    (conservative under degraded sensors)
  +0.3  keep_normal when risk_score < 0.3            (correctly did not over-escalate)
  -1.0  keep_normal when risk_score > 0.7            (ignored high risk)
  -0.8  raise_alert when risk_score < 0.2            (escalated low-risk noise)
  -0.5  lower_alert when risk_score > 0.6            (de-escalated real risk)
  -1.5  allocate_resource when system_load < 0.2     (wasted resources)
  -0.2  any action while inference_latency_normalized > 0.8  (latency cost)

Plus one documented addition to the spec values (justified — keeps the HITL
suggestion rate in the required operational band and mirrors the "do not
escalate everything to a human" principle, the HITL analogue of the
"escalate-everything-as-critical" penalty):

  -0.5  request_hitl when risk_score < 0.6 AND
        fusion_confidence >= 0.4                      (unnecessary human escalation)

Without this term the optimal policy degenerates to *always* requesting human
review (HITL rate 1.0), because HITL otherwise has no downside; the penalty
restores a discriminative policy with a realistic HITL suggestion rate.

These are the canonical REWARD_V1 constants. ``reward_version`` in the report is
exactly ``"REWARD_V1"``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from apps.learning.rl.config import OBSERVATION_NAMES, REWARD_VERSION

# Observation index lookup (kept local + explicit for readability).
_IDX = {name: i for i, name in enumerate(OBSERVATION_NAMES)}

# Action ids (mirror config.ACTION_NAMES order).
A_KEEP_NORMAL = 0
A_RAISE_ALERT = 1
A_LOWER_ALERT = 2
A_SUGGEST_CONSERVATIVE = 3
A_REQUEST_HITL = 4
A_ALLOCATE_RESOURCE = 5

# REWARD_V1 magnitudes (item 6B-5).
R_RAISE_HIGH_RISK = 1.5
R_HITL_APPROPRIATE = 1.0
R_CONSERVATIVE_DEGRADED = 0.5
R_KEEP_LOW_RISK = 0.3
P_IGNORE_HIGH_RISK = -1.0
P_ESCALATE_LOW_RISK = -0.8
P_LOWER_HIGH_RISK = -0.5
P_WASTE_RESOURCE = -1.5
P_LATENCY_COST = -0.2
P_HITL_UNNECESSARY = -0.5  # documented addition (see module docstring)

# Thresholds used by the reward logic.
HIGH_RISK = 0.7
MED_RISK = 0.6
LOW_RISK = 0.3
VERY_LOW_RISK = 0.2
LOW_CONFIDENCE = 0.4
HIGH_DROPOUT = 0.5
LOW_LOAD = 0.2
HIGH_LATENCY = 0.8


@dataclass
class RewardBreakdown:
    """Per-step reward components (used by tests + the policy summary)."""

    total: float
    is_unsafe_action: bool
    is_hitl_suggestion: bool


def compute_reward(obs: np.ndarray, action: int) -> RewardBreakdown:
    """Compute the REWARD_V1 reward + safety flags for one (obs, action) step.

    ``obs`` is the 10-dim observation BEFORE the transition (the state the agent
    saw when it chose ``action``). Returns a :class:`RewardBreakdown`.
    """
    risk = float(obs[_IDX["risk_score"]])
    confidence = float(obs[_IDX["fusion_confidence"]])
    dropout = float(obs[_IDX["sensor_dropout_ratio"]])
    latency = float(obs[_IDX["inference_latency_normalized"]])
    load = float(obs[_IDX["system_load_normalized"]])

    reward = 0.0

    # --- positive, safe operational behavior ---
    if action == A_RAISE_ALERT and risk > HIGH_RISK:
        reward += R_RAISE_HIGH_RISK
    if action == A_REQUEST_HITL and (risk > MED_RISK or confidence < LOW_CONFIDENCE):
        reward += R_HITL_APPROPRIATE
    if action == A_SUGGEST_CONSERVATIVE and dropout > HIGH_DROPOUT:
        reward += R_CONSERVATIVE_DEGRADED
    if action == A_KEEP_NORMAL and risk < LOW_RISK:
        reward += R_KEEP_LOW_RISK

    # --- penalties for clearly inappropriate / wasteful actions ---
    if action == A_KEEP_NORMAL and risk > HIGH_RISK:
        reward += P_IGNORE_HIGH_RISK
    if action == A_RAISE_ALERT and risk < VERY_LOW_RISK:
        reward += P_ESCALATE_LOW_RISK
    if action == A_LOWER_ALERT and risk > MED_RISK:
        reward += P_LOWER_HIGH_RISK
    if action == A_ALLOCATE_RESOURCE and load < LOW_LOAD:
        reward += P_WASTE_RESOURCE
    if action == A_REQUEST_HITL and risk < MED_RISK and confidence >= LOW_CONFIDENCE:
        reward += P_HITL_UNNECESSARY

    # --- simulated latency cost ---
    if latency > HIGH_LATENCY:
        reward += P_LATENCY_COST

    return RewardBreakdown(
        total=float(reward),
        is_unsafe_action=is_unsafe_action(obs, action),
        is_hitl_suggestion=(action == A_REQUEST_HITL),
    )


def is_unsafe_action(obs: np.ndarray, action: int) -> bool:
    """Operational definition of an *unsafe* (clearly inappropriate) action.

    item 6B-7: escalating clear low-risk noise, or de-escalating clear high
    risk. These are the decisions a well-trained policy should rarely take.
    """
    risk = float(obs[_IDX["risk_score"]])
    if action == A_RAISE_ALERT and risk < LOW_RISK:
        return True
    if action == A_LOWER_ALERT and risk > MED_RISK:
        return True
    return False


# Convenience export so the report can record the canonical version string.
__all__ = [
    "REWARD_VERSION",
    "RewardBreakdown",
    "compute_reward",
    "is_unsafe_action",
]
