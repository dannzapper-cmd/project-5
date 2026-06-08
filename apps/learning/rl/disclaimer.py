"""Single source of truth for the Phase 6B RL safety disclaimer."""

from __future__ import annotations

DISCLAIMER = (
    "Synthetic RL operational policy. No real patient data. No medical decisions. "
    "Human review required for high-risk actions."
)

# Longer-form safety/scope statement reused in reports, the safety envelope, and docs.
SAFETY_SCOPE = (
    "This reinforcement learning module only optimizes synthetic operational "
    "triage suggestions (alert prioritization, conservative threshold hints, "
    "simulated resource allocation, and human-in-the-loop escalation). It does "
    "NOT make medical decisions, does NOT diagnose or treat, does NOT control "
    "real hardware or robots, and never takes irreversible or safety-critical "
    "actions. Human review is required for high-risk or low-confidence "
    "situations. Trained and evaluated on synthetic data only."
)
