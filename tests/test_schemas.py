"""Phase 0 schema validation tests (no external services)."""

import pytest
from apps.api.app.schemas.events import (
    AgentTraceEventV1,
    DecisionEventV1,
    HealthEventV1,
    ModelScoreEventV1,
    SensorEventV1,
)
from pydantic import ValidationError


def test_valid_sensor_event_v1() -> None:
    event = SensorEventV1(
        trace_id="trace-001",
        source="sensor-emg-node-1",
        signal_type="emg",
        unit="mV",
        values=[0.12, 0.15, 0.11],
        quality=0.95,
        metadata={"node_id": "emg-01"},
    )
    assert event.schema_version == "v1"
    assert event.signal_type == "emg"
    assert len(event.values) == 3


def test_invalid_confidence_or_quality() -> None:
    with pytest.raises(ValidationError):
        SensorEventV1(
            trace_id="trace-002",
            source="sensor-emg-node-1",
            signal_type="emg",
            unit="mV",
            values=[0.1],
            quality=1.5,
        )

    with pytest.raises(ValidationError):
        ModelScoreEventV1(
            trace_id="trace-003",
            source="edge-inference",
            model_name="emg-tiny",
            model_version="0.0.1",
            score=0.8,
            confidence=-0.1,
            latency_ms=12.0,
            input_event_id="evt-1",
            output_label="normal",
        )


def test_valid_decision_event_with_human_confirmation() -> None:
    event = DecisionEventV1(
        trace_id="trace-004",
        source="agent-orchestrator",
        decision_type="session_pause",
        risk_level="high",
        confidence=0.62,
        recommended_action="pause_rehab_session",
        requires_human_confirmation=True,
        rationale="Elevated anomaly score with low fusion confidence.",
        related_event_ids=["evt-1", "evt-2"],
    )
    assert event.requires_human_confirmation is True
    assert event.risk_level == "high"


def test_valid_model_score_event_v1() -> None:
    event = ModelScoreEventV1(
        trace_id="trace-005",
        source="edge-inference",
        model_name="imu-anomaly",
        model_version="0.1.0",
        score=0.73,
        confidence=0.88,
        latency_ms=4.2,
        input_event_id="sensor-evt-99",
        output_label="anomaly",
    )
    assert event.latency_ms >= 0


def test_valid_agent_trace_event_v1() -> None:
    event = AgentTraceEventV1(
        trace_id="trace-006",
        source="langgraph-runtime",
        agent_name="safety-coordinator",
        step_name="evaluate_risk",
        input_summary="Fusion confidence below threshold.",
        output_summary="Recommend operator confirmation.",
        confidence=0.71,
        tool_calls=["fetch_fusion_state", "check_safety_policy"],
        requires_human_review=True,
    )
    assert event.requires_human_review is True


def test_valid_health_event_v1() -> None:
    event = HealthEventV1(
        trace_id="trace-007",
        source="axon-api",
        component="redis-streams",
        status="degraded",
        latency_ms=120.0,
        message="Elevated consumer lag detected.",
        metadata={"stream": "axon:v1:stream:sensors:emg"},
    )
    assert event.status == "degraded"


def test_sensor_event_empty_values_rejected() -> None:
    with pytest.raises(ValidationError):
        SensorEventV1(
            trace_id="trace-008",
            source="sensor-imu-node-1",
            signal_type="imu",
            unit="g",
            values=[],
            quality=0.9,
        )


def test_negative_latency_rejected() -> None:
    with pytest.raises(ValidationError):
        HealthEventV1(
            trace_id="trace-009",
            source="axon-api",
            component="mqtt-bridge",
            status="ok",
            latency_ms=-1.0,
            message="Invalid latency.",
        )
