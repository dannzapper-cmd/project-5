"""Phase 6B RL environment tests (Gymnasium required).

Skipped automatically when the learning-profile dependencies are not installed
(e.g. core CI), and run locally after ``make learning-rl-install``.

Synthetic RL operational policy. No real patient data. No medical decisions.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
gymnasium = pytest.importorskip("gymnasium")

from apps.learning.rl.environment import AxonTriageEnvV1  # noqa: E402
from apps.learning.rl.reward import (  # noqa: E402
    A_KEEP_NORMAL,
    A_RAISE_ALERT,
    A_REQUEST_HITL,
)
from gymnasium import spaces  # noqa: E402

_IDX_RISK = 0
_IDX_HITL = 9


def test_class_name_is_exact():
    assert AxonTriageEnvV1.__name__ == "AxonTriageEnvV1"
    assert AxonTriageEnvV1().name == "AxonTriageEnvV1"


def test_observation_space_is_box_10():
    env = AxonTriageEnvV1()
    assert isinstance(env.observation_space, spaces.Box)
    assert env.observation_space.shape == (10,)
    assert env.observation_space.dtype == np.float32
    assert np.allclose(env.observation_space.low, 0.0)
    assert np.allclose(env.observation_space.high, 1.0)


def test_action_space_is_discrete_6():
    env = AxonTriageEnvV1()
    assert isinstance(env.action_space, spaces.Discrete)
    assert env.action_space.n == 6
    assert len(env.action_names) == 6


def test_reset_returns_obs_info_tuple():
    """Gymnasium (not legacy gym) API: reset() -> (obs, info)."""
    env = AxonTriageEnvV1()
    out = env.reset(seed=42)
    assert isinstance(out, tuple) and len(out) == 2
    obs, info = out
    assert obs.shape == (10,)
    assert obs.dtype == np.float32
    assert isinstance(info, dict)
    assert env.observation_space.contains(obs)


def test_step_returns_five_tuple():
    """Gymnasium API: step() -> (obs, reward, terminated, truncated, info)."""
    env = AxonTriageEnvV1()
    env.reset(seed=42)
    obs, reward, terminated, truncated, info = env.step(1)
    assert obs.shape == (10,)
    assert env.observation_space.contains(obs)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_gymnasium_env_checker_passes():
    from gymnasium.utils.env_checker import check_env

    check_env(AxonTriageEnvV1())


def test_step_produces_state_transitions_request_hitl_clears_flag():
    """item 6B-4 / BLOCKER 6B-2: request_hitl clears human_review_required."""
    env = AxonTriageEnvV1()
    env.reset(seed=7)
    env._state[_IDX_HITL] = 1.0
    env._state[_IDX_RISK] = 0.8
    obs, *_ = env.step(A_REQUEST_HITL)
    assert obs[_IDX_HITL] == 0.0


def test_keep_normal_does_not_reduce_high_risk():
    """item 6B-4 / BLOCKER 6B-2: ignoring high risk never decreases it."""
    env = AxonTriageEnvV1()
    env.reset(seed=11)
    env._state[_IDX_RISK] = 0.9
    obs, *_ = env.step(A_KEEP_NORMAL)
    assert obs[_IDX_RISK] >= 0.9 - 1e-6


def test_raise_alert_propagates_risk_upward():
    env = AxonTriageEnvV1()
    env.reset(seed=13)
    env._state[_IDX_RISK] = 0.5
    obs, *_ = env.step(A_RAISE_ALERT)
    # Escalation propagates risk slightly upward (modulo bounded noise).
    assert obs[_IDX_RISK] > 0.5 - 0.05


def test_episode_truncates_at_max_steps():
    env = AxonTriageEnvV1(max_episode_steps=5)
    env.reset(seed=1)
    truncated = False
    for _ in range(5):
        _, _, terminated, truncated, _ = env.step(A_REQUEST_HITL)
        if terminated or truncated:
            break
    assert truncated or terminated


def test_actions_have_consequence_observations_change():
    """Observations must not be static/identical regardless of action."""
    env = AxonTriageEnvV1()
    obs0, _ = env.reset(seed=21)
    obs1, *_ = env.step(A_RAISE_ALERT)
    assert not np.array_equal(obs0, obs1)
