#!/usr/bin/env python3
"""Lightweight Phase 0 development validation (no external services)."""

from __future__ import annotations

from apps.api.app.schemas.events import DecisionEventV1, SensorEventV1


def main() -> None:
    sensor = SensorEventV1(
        trace_id="dev-check-trace",
        source="dev-check",
        signal_type="emg",
        unit="mV",
        values=[0.1, 0.2, 0.15],
        quality=0.99,
    )
    decision = DecisionEventV1(
        trace_id="dev-check-trace",
        source="dev-check",
        decision_type="noop",
        risk_level="low",
        confidence=0.95,
        recommended_action="continue",
        requires_human_confirmation=False,
        rationale="Phase 0 schema validation only.",
    )
    assert sensor.event_id
    assert decision.event_id
    print("AXON Phase 0 dev check: schemas import and instantiate successfully.")


if __name__ == "__main__":
    main()
