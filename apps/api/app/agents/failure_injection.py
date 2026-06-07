"""Controlled failure injection for Phase 3 operational simulation."""

from __future__ import annotations

import os
import time

_active_injections: dict[str, float] = {}
AUTO_RESET_SECONDS = int(os.getenv("AXON_FAILURE_INJECTION_AUTO_RESET_SECONDS", "30"))

SUPPORTED_SCENARIOS = frozenset(
    {"sensor_dropout", "corrupt_event", "model_low_confidence", "stale_telemetry"}
)


def activate_injection(scenario: str) -> None:
    """Record scenario activation timestamp."""
    if scenario not in SUPPORTED_SCENARIOS:
        raise ValueError(f"Unknown injection scenario: {scenario}")
    _active_injections[scenario] = time.time()


def reset_injections() -> None:
    """Clear all active failure injections."""
    _active_injections.clear()


def evict_expired_injections() -> None:
    """Remove injections past auto-reset TTL."""
    now = time.time()
    expired = [k for k, v in _active_injections.items() if now - v >= AUTO_RESET_SECONDS]
    for key in expired:
        del _active_injections[key]


def is_active(scenario: str) -> bool:
    """Return True if scenario is currently active."""
    evict_expired_injections()
    return scenario in _active_injections


def active_scenarios() -> list[str]:
    """Return list of currently active injection scenarios."""
    evict_expired_injections()
    return list(_active_injections.keys())
