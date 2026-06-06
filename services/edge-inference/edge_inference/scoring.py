"""Map ONNX output to ModelScoreEventV1 — single signal only, no fusion."""

from __future__ import annotations

from datetime import UTC, datetime

from apps.api.app.schemas.events import ModelScoreEventV1, SensorEventV1

from edge_inference.model_registry import ModelMetadata
from edge_inference.onnx_runner import InferenceResult


def build_model_score_event(
    sensor_event: SensorEventV1,
    metadata: ModelMetadata,
    inference: InferenceResult,
    source: str,
) -> ModelScoreEventV1:
    """Create ModelScoreEventV1 from one signal's ONNX output."""
    confidence = max(0.0, min(1.0, sensor_event.quality * (1.0 - abs(inference.score - 0.5))))
    return ModelScoreEventV1(
        trace_id=sensor_event.trace_id,
        source=source,
        model_name=metadata.model_name,
        model_version=metadata.model_version,
        score=inference.score,
        confidence=confidence,
        latency_ms=inference.latency_ms,
        input_event_id=sensor_event.event_id,
        output_label=inference.label,
        metadata={
            "signal_type": sensor_event.signal_type,
            "input_signal": sensor_event.signal_type,
            "safety_note": metadata.safety_note,
        },
        timestamp=datetime.now(UTC),
    )
