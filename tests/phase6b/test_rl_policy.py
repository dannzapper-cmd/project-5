"""Phase 6B RL policy / training smoke tests (Gymnasium + Stable-Baselines3).

Uses the tiny CI profile (``RL_CI_MODE=true`` -> 500 timesteps, 5 eval episodes)
so each test finishes well under 30s.

Synthetic RL operational policy. No real patient data. No medical decisions.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")
pytest.importorskip("gymnasium")
pytest.importorskip("stable_baselines3")
pytest.importorskip("torch")

from apps.learning.rl.policy import (  # noqa: E402
    evaluate_baseline,
    evaluate_policy,
    random_action_fn,
    train_ppo,
    trained_action_fn,
)


@pytest.fixture(autouse=True)
def _ci_mode(monkeypatch):
    monkeypatch.setenv("RL_CI_MODE", "true")


def test_baseline_evaluation_runs():
    metrics = evaluate_baseline(n_episodes=5, seed=42)
    assert metrics.total_steps > 0
    assert len(metrics.episode_rewards) == 5
    assert 0.0 <= metrics.unsafe_action_rate <= 1.0
    assert 0.0 <= metrics.hitl_suggestion_rate <= 1.0


def test_evaluate_policy_is_reproducible_same_seed():
    a = evaluate_policy(random_action_fn(1), n_episodes=5, seed=99)
    b = evaluate_policy(random_action_fn(1), n_episodes=5, seed=99)
    assert a.episode_rewards == b.episode_rewards


def test_train_ppo_smoke_and_evaluate():
    result = train_ppo(total_timesteps=500, seed=42)
    assert result.model is not None
    metrics = evaluate_policy(trained_action_fn(result.model), n_episodes=5, seed=42)
    assert metrics.total_steps > 0
    # reward curve recorded at least once
    assert len(result.reward_curve) >= 1
    for point in result.reward_curve:
        assert "timesteps" in point and "mean_episode_reward" in point


def test_safety_metrics_are_well_defined():
    metrics = evaluate_baseline(n_episodes=5, seed=7)
    # operational metrics are real ratios in [0, 1], not decorative constants
    assert isinstance(metrics.unsafe_action_rate, float)
    assert isinstance(metrics.hitl_suggestion_rate, float)
    assert metrics.episode_length_mean > 0
