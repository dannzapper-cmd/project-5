"""Phase 6B — RL Micro-module (synthetic safe operational triage policy).

This package adds a tiny, reproducible reinforcement learning micro-module to
AXON. A small Gymnasium environment (:class:`~apps.learning.rl.environment.
AxonTriageEnvV1`) simulates *operational* decision-making for AXON — alert
prioritization, conservative threshold suggestions, simulated resource
allocation, and human-in-the-loop escalation. A short PPO training run (Stable-
Baselines3) learns a policy that beats a random baseline; everything is CPU-only,
fixed-seed, local-first, and logged to a local file-based MLflow store.

SAFETY / SCOPE
--------------
- Synthetic RL operational policy. No real patient data. No medical decisions.
  Human review required for high-risk actions.
- The policy only optimizes synthetic operational triage/suggestions. It does
  NOT diagnose, treat, recommend clinical actions, control real hardware/robots,
  or take irreversible / safety-critical actions.
- Phase 6B only — this package does NOT implement Phase 7 and does NOT modify
  ROS2 / Nav2 / SLAM or Phase 6A federated learning.
"""

from apps.learning.rl.disclaimer import DISCLAIMER

__all__ = ["DISCLAIMER"]
