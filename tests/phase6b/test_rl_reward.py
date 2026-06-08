"""Phase 6B REWARD_V1 reward-function tests.

These validate that the reward gives a positive signal for safe operational
actions and penalizes clearly inappropriate / unsafe ones, with the exact
documented magnitudes (item 6B-5).

Synthetic RL operational policy. No real patient data. No medical decisions.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from apps.learning.rl.config import OBSERVATION_NAMES, REWARD_VERSION  # noqa: E402
from apps.learning.rl.reward import (  # noqa: E402
    A_ALLOCATE_RESOURCE,
    A_KEEP_NORMAL,
    A_LOWER_ALERT,
    A_RAISE_ALERT,
    A_REQUEST_HITL,
    A_SUGGEST_CONSERVATIVE,
    P_HITL_UNNECESSARY,
    P_IGNORE_HIGH_RISK,
    R_HITL_APPROPRIATE,
    R_RAISE_HIGH_RISK,
    compute_reward,
    is_unsafe_action,
)

_IDX = {name: i for i, name in enumerate(OBSERVATION_NAMES)}


def _obs(**kw) -> np.ndarray:
    """Build a neutral observation, overriding named features."""
    o = np.full(10, 0.5, dtype=np.float32)
    o[_IDX["fusion_confidence"]] = 0.8  # high confidence by default
    o[_IDX["inference_latency_normalized"]] = 0.0
    o[_IDX["system_load_normalized"]] = 0.8
    o[_IDX["sensor_dropout_ratio"]] = 0.0
    for name, val in kw.items():
        o[_IDX[name]] = val
    return o


def test_reward_version_constant():
    assert REWARD_VERSION == "REWARD_V1"


def test_reward_positive_for_raise_on_high_risk():
    r = compute_reward(_obs(risk_score=0.9), A_RAISE_ALERT)
    assert r.total == pytest.approx(R_RAISE_HIGH_RISK)
    assert r.total > 0


def test_reward_positive_for_hitl_on_low_confidence():
    r = compute_reward(_obs(risk_score=0.4, fusion_confidence=0.2), A_REQUEST_HITL)
    assert r.total == pytest.approx(R_HITL_APPROPRIATE)
    assert r.is_hitl_suggestion is True


def test_reward_positive_for_keep_on_low_risk():
    r = compute_reward(_obs(risk_score=0.1), A_KEEP_NORMAL)
    assert r.total > 0


def test_reward_positive_for_conservative_on_sensor_dropout():
    r = compute_reward(_obs(risk_score=0.4, sensor_dropout_ratio=0.8), A_SUGGEST_CONSERVATIVE)
    assert r.total > 0


def test_reward_penalizes_ignoring_high_risk():
    r = compute_reward(_obs(risk_score=0.9), A_KEEP_NORMAL)
    assert r.total == pytest.approx(P_IGNORE_HIGH_RISK)
    assert r.total < 0


def test_reward_penalizes_escalating_low_risk_noise():
    r = compute_reward(_obs(risk_score=0.1), A_RAISE_ALERT)
    assert r.total < 0


def test_reward_penalizes_lowering_high_risk():
    r = compute_reward(_obs(risk_score=0.8), A_LOWER_ALERT)
    assert r.total < 0


def test_reward_penalizes_wasting_resources():
    r = compute_reward(_obs(risk_score=0.4, system_load_normalized=0.1), A_ALLOCATE_RESOURCE)
    assert r.total < 0


def test_reward_penalizes_unnecessary_hitl():
    """Escalating to a human when calm + confident wastes human attention."""
    r = compute_reward(_obs(risk_score=0.2, fusion_confidence=0.9), A_REQUEST_HITL)
    assert r.total == pytest.approx(P_HITL_UNNECESSARY)
    assert r.total < 0


def test_is_unsafe_action_flags_inappropriate_escalation():
    assert is_unsafe_action(_obs(risk_score=0.1), A_RAISE_ALERT) is True
    assert is_unsafe_action(_obs(risk_score=0.9), A_LOWER_ALERT) is True
    assert is_unsafe_action(_obs(risk_score=0.9), A_RAISE_ALERT) is False
    assert is_unsafe_action(_obs(risk_score=0.1), A_KEEP_NORMAL) is False


def test_latency_cost_applied():
    high_lat = compute_reward(
        _obs(risk_score=0.9, inference_latency_normalized=0.95), A_RAISE_ALERT
    )
    no_lat = compute_reward(
        _obs(risk_score=0.9, inference_latency_normalized=0.0), A_RAISE_ALERT
    )
    assert high_lat.total < no_lat.total
