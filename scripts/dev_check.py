#!/usr/bin/env python3
"""Lightweight Phase 2 development validation (no external services)."""

from __future__ import annotations

from apps.api.app.schemas.events import ModelScoreEventV1, SensorEventV1
from apps.api.app.telemetry.model_score_streams import MODEL_SCORE_STREAM

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
    score = ModelScoreEventV1(
        trace_id="dev-check-trace",
        source="edge-inference",
        model_name="emg_anomaly",
        model_version="v0",
        score=0.5,
        confidence=0.9,
        latency_ms=2.0,
        input_event_id=sensor.event_id,
        output_label="normal",
    )
    batch = generate_event_batch(GeneratorConfig(axon_seed=1), tick=0, seed=1)
    assert sensor.event_id
    assert score.event_id
    assert len(batch) == 5
    assert MODEL_SCORE_STREAM == "axon:v1:stream:model_scores"
    print("AXON Phase 2 dev check: schemas, generator batch, and model score stream OK.")


if __name__ == "__main__":
    main()
