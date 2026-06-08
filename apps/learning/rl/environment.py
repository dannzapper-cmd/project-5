"""AxonTriageEnvV1 — a tiny Gymnasium environment for synthetic operational triage.

This is a Gymnasium-compatible (Farama) environment, NOT legacy ``gym``:
``reset()`` returns ``(obs, info)`` and ``step()`` returns
``(obs, reward, terminated, truncated, info)``.

The environment simulates *safe operational decision-making* for AXON. The agent
observes a synthetic operational state (risk, fusion confidence, anomaly count,
sensor dropout, latency, system load, alert severity, robot-state risk, recent
false-positive rate, and a human-review flag) and picks one of six safe
operational actions (keep/raise/lower alert, suggest a conservative threshold,
request human-in-the-loop review, or allocate a simulated resource).

The dynamics are real transitions, not a static observation generator: actions
change the next observable state (item 6B-4). Reward is REWARD_V1 (see
:mod:`apps.learning.rl.reward`).

SAFETY: synthetic only. No real patient data. No medical decisions. No hardware
control. Actions are operational suggestions; high-risk/low-confidence states
must be escalated to a human (``request_hitl``).
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from apps.learning.rl.config import (
    ACTION_COUNT,
    ACTION_NAMES,
    ENV_NAME,
    MAX_EPISODE_STEPS,
    OBSERVATION_DIM,
    OBSERVATION_NAMES,
)
from apps.learning.rl.reward import (
    A_KEEP_NORMAL,
    A_RAISE_ALERT,
    A_REQUEST_HITL,
    compute_reward,
)

_IDX = {name: i for i, name in enumerate(OBSERVATION_NAMES)}

# Per-step zero-mean Gaussian observation noise (item 6B-4).
_NOISE_STD = 0.05


class AxonTriageEnvV1(gym.Env):
    """Synthetic operational-triage decision environment (10 obs, 6 actions)."""

    metadata = {"render_modes": ["ansi"]}

    name = ENV_NAME
    observation_names = OBSERVATION_NAMES
    action_names = ACTION_NAMES

    def __init__(self, max_episode_steps: int = MAX_EPISODE_STEPS) -> None:
        super().__init__()
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBSERVATION_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(ACTION_COUNT)
        self.max_episode_steps = int(max_episode_steps)
        self._state = np.zeros(OBSERVATION_DIM, dtype=np.float32)
        self._steps = 0

    # --- helpers ----------------------------------------------------------
    def _clip(self, arr: np.ndarray) -> np.ndarray:
        return np.clip(arr, 0.0, 1.0).astype(np.float32)

    def _sample_situation(self) -> np.ndarray:
        """Draw a fresh, broadly-distributed synthetic operational state.

        Every feature is drawn uniformly so the agent sees the full state space.
        ``human_review_required`` is derived from the sampled risk/confidence.
        """
        rng = self.np_random
        s = rng.uniform(0.0, 1.0, size=OBSERVATION_DIM).astype(np.float32)
        risk = s[_IDX["risk_score"]]
        conf = s[_IDX["fusion_confidence"]]
        s[_IDX["human_review_required"]] = 1.0 if (risk > 0.6 or conf < 0.4) else 0.0
        return self._clip(s)

    # --- Gymnasium API ----------------------------------------------------
    def reset(
        self, *, seed: int | None = None, options: dict | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        self._steps = 0
        self._state = self._sample_situation()
        return self._state.copy(), {"step": self._steps}

    def step(
        self, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        action = int(action)
        obs_before = self._state.copy()

        # Reward is computed from the state the agent SAW (obs_before).
        breakdown = compute_reward(obs_before, action)

        next_state = self._transition(obs_before, action)
        self._state = next_state
        self._steps += 1

        terminated = bool(next_state[_IDX["risk_score"]] >= 1.0 - 1e-6)
        truncated = bool(self._steps >= self.max_episode_steps)

        info = {
            "step": self._steps,
            "action_name": ACTION_NAMES[action],
            "is_unsafe_action": breakdown.is_unsafe_action,
            "is_hitl_suggestion": breakdown.is_hitl_suggestion,
            "obs_before": obs_before,
        }
        return next_state.copy(), breakdown.total, terminated, truncated, info

    # --- dynamics ---------------------------------------------------------
    def _transition(self, state: np.ndarray, action: int) -> np.ndarray:
        """Produce the next observable state (item 6B-4 transition rules).

        ``risk_score`` is a genuinely dynamic state variable that responds to the
        action taken (consequence): escalation propagates it, human review eases
        it, and ignoring a high risk lets it climb. The other (exogenous,
        contextual) features are resampled fresh each step so the agent sees the
        full state space; controlled Gaussian noise is added to everything.
        """
        rng = self.np_random
        ri = _IDX["risk_score"]
        hi = _IDX["human_review_required"]
        risk_before = float(state[ri])

        # Exogenous contextual signals (confidence, dropout, latency, load, etc.)
        # are resampled each step — this is the per-step synthetic situation.
        s = self._sample_situation()

        # --- risk_score dynamics (responds to the action) ---
        if action == A_RAISE_ALERT:
            # Escalation acknowledges risk; it propagates slightly upward.
            risk = risk_before + float(rng.uniform(0.05, 0.15))
        elif action == A_REQUEST_HITL:
            # Human review attended -> risk eased.
            risk = risk_before - 0.1
        elif action == A_KEEP_NORMAL and risk_before > 0.7:
            # Ignoring an already-high risk lets it climb further (never down).
            risk = risk_before + 0.05
        else:
            # Otherwise risk mean-reverts toward the mid-range so both high- and
            # low-risk situations recur over an episode.
            risk = 0.85 * risk_before + 0.15 * 0.5

        # Occasional exogenous risk event keeps high-risk states appearing.
        if rng.random() < 0.1:
            risk += float(rng.uniform(0.1, 0.3))

        risk += float(rng.normal(0.0, _NOISE_STD))

        # Guarantee: ignoring/escalating a high risk never *decreases* it, even
        # after noise (BLOCKER 6B-2). request_hitl is the only deliberate easing.
        if (action == A_KEEP_NORMAL and risk_before > 0.7) or action == A_RAISE_ALERT:
            risk = max(risk, risk_before)

        s[ri] = risk

        # human_review_required: cleared when this step attended to review,
        # otherwise derived from the (new) risk/confidence.
        if action == A_REQUEST_HITL:
            s[hi] = 0.0
        else:
            conf = float(s[_IDX["fusion_confidence"]])
            s[hi] = 1.0 if (s[ri] > 0.6 or conf < 0.4) else 0.0

        return self._clip(s)

    def render(self) -> str:  # pragma: no cover - convenience only
        parts = [f"{n}={v:.2f}" for n, v in zip(OBSERVATION_NAMES, self._state, strict=True)]
        return f"[{self._steps}] " + " ".join(parts)
