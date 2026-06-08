"""Training, baseline, and evaluation for the AxonTriageEnvV1 RL micro-module.

Primary path: Stable-Baselines3 PPO (CPU, short, fixed-seed). The baseline is a
**random policy** (``action_space.sample()``) evaluated on the SAME episodes as
the trained policy so the comparison is fair (item 6B-6). Evaluation also
computes the operational safety metrics (``unsafe_action_rate``,
``hitl_suggestion_rate``, ``episode_length_mean``) used by the report and the
dashboard.

Everything is CPU-only, deterministic for a fixed seed, and CI-friendly (tiny
timesteps when ``RL_CI_MODE=true``). No medical decisions, no hardware control —
the policy only chooses synthetic operational triage actions.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from apps.learning.rl.config import ACTION_COUNT
from apps.learning.rl.environment import AxonTriageEnvV1

ALGORITHM = "PPO (Stable-Baselines3)"

ActionFn = Callable[[np.ndarray], int]


def set_global_seeds(seed: int) -> None:
    """Seed random + numpy (and torch if available) for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    try:  # torch is a learning-profile dep; degrade gracefully if absent.
        import torch

        torch.manual_seed(seed)
        torch.use_deterministic_algorithms(False)
    except Exception:  # noqa: BLE001 - torch optional at import time
        pass


@dataclass
class EvalMetrics:
    """Aggregate evaluation metrics over ``n_episodes`` complete episodes."""

    mean_reward: float
    episode_rewards: list[float] = field(default_factory=list)
    unsafe_action_rate: float = 0.0
    hitl_suggestion_rate: float = 0.0
    episode_length_mean: float = 0.0
    total_steps: int = 0

    def as_dict(self) -> dict:
        return {
            "mean_reward": round(self.mean_reward, 6),
            "unsafe_action_rate": round(self.unsafe_action_rate, 6),
            "hitl_suggestion_rate": round(self.hitl_suggestion_rate, 6),
            "episode_length_mean": round(self.episode_length_mean, 6),
            "total_steps": self.total_steps,
        }


def evaluate_policy(
    action_fn: ActionFn,
    *,
    n_episodes: int,
    seed: int,
    max_episode_steps: int | None = None,
) -> EvalMetrics:
    """Run ``n_episodes`` and aggregate reward + operational safety metrics.

    Each episode resets the env with ``seed + episode_index`` so a given policy
    is evaluated on a fixed, reproducible set of synthetic situations.
    """
    env = AxonTriageEnvV1() if max_episode_steps is None else AxonTriageEnvV1(max_episode_steps)
    episode_rewards: list[float] = []
    unsafe_steps = 0
    hitl_steps = 0
    total_steps = 0

    for ep in range(n_episodes):
        obs, _ = env.reset(seed=seed + ep)
        done = False
        ep_reward = 0.0
        while not done:
            action = int(action_fn(obs))
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += float(reward)
            total_steps += 1
            if info.get("is_unsafe_action"):
                unsafe_steps += 1
            if info.get("is_hitl_suggestion"):
                hitl_steps += 1
            done = terminated or truncated
        episode_rewards.append(ep_reward)

    steps = max(1, total_steps)
    return EvalMetrics(
        mean_reward=float(np.mean(episode_rewards)) if episode_rewards else 0.0,
        episode_rewards=[round(float(r), 6) for r in episode_rewards],
        unsafe_action_rate=unsafe_steps / steps,
        hitl_suggestion_rate=hitl_steps / steps,
        episode_length_mean=total_steps / max(1, n_episodes),
        total_steps=total_steps,
    )


def random_action_fn(seed: int) -> ActionFn:
    """Deterministic random baseline over the discrete action space."""
    rng = np.random.default_rng(seed)
    return lambda _obs: int(rng.integers(0, ACTION_COUNT))


def evaluate_baseline(*, n_episodes: int, seed: int) -> EvalMetrics:
    """Evaluate the random baseline policy (item 6B-6)."""
    return evaluate_policy(random_action_fn(seed), n_episodes=n_episodes, seed=seed)


@dataclass
class TrainResult:
    model: object
    reward_curve: list[dict]  # [{"timesteps": int, "mean_episode_reward": float}, ...]


def train_ppo(*, total_timesteps: int, seed: int) -> TrainResult:
    """Train a short PPO policy on AxonTriageEnvV1 (CPU, fixed-seed).

    Raises ImportError if Stable-Baselines3 is unavailable (learning profile).
    """
    set_global_seeds(seed)
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.monitor import Monitor

    env = Monitor(AxonTriageEnvV1())
    env.reset(seed=seed)
    env.action_space.seed(seed)

    reward_curve: list[dict] = []

    class _RewardCurveCallback(BaseCallback):
        def _on_step(self) -> bool:
            return True

        def _on_rollout_end(self) -> None:
            buf = self.model.ep_info_buffer
            if buf:
                mean_r = float(np.mean([ep["r"] for ep in buf]))
                reward_curve.append(
                    {
                        "timesteps": int(self.num_timesteps),
                        "mean_episode_reward": round(mean_r, 6),
                    }
                )

    # ent_coef=0.03 keeps enough exploration for the policy to discover the
    # human-in-the-loop region (otherwise PPO collapses to a single safe action
    # and the HITL suggestion rate degenerates to 0). These are CPU-light and
    # reproducible for a fixed seed.
    model = PPO(
        "MlpPolicy",
        env,
        seed=seed,
        device="cpu",
        n_steps=512,
        batch_size=64,
        n_epochs=6,
        ent_coef=0.03,
        verbose=0,
        policy_kwargs={"net_arch": [64, 64]},
    )
    model.learn(total_timesteps=total_timesteps, callback=_RewardCurveCallback())
    return TrainResult(model=model, reward_curve=reward_curve)


def trained_action_fn(model: object) -> ActionFn:
    """Wrap a trained SB3 model as a deterministic action function."""

    def _fn(obs: np.ndarray) -> int:
        action, _ = model.predict(obs, deterministic=True)  # type: ignore[attr-defined]
        return int(action)

    return _fn
