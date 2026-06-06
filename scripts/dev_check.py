#!/usr/bin/env python3
"""Lightweight Phase 1 development validation (no external services)."""

from __future__ import annotations

from apps.api.app.schemas.events import DecisionEventV1, SensorEventV1

from axon_generators.config import GeneratorConfig
from axon_generators.generator import generate_event_batch


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
        rationale="Phase 1 schema validation only.",
    )
    batch = generate_event_batch(GeneratorConfig(axon_seed=1), tick=0, seed=1)
    assert sensor.event_id
    assert decision.event_id
    assert len(batch) == 5
    print("AXON Phase 1 dev check: schemas and generator batch OK.")


if __name__ == "__main__":
    main()
