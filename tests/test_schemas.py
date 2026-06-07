"""Phase 0/3 schema validation tests (no external services)."""

from datetime import UTC, datetime

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


def test_valid_decision_event_v1() -> None:
    now = datetime.now(UTC)
    event = DecisionEventV1(
        trace_id="trace-004",
        source="axon-api",
        session_id="session-synthetic-001",
        input_window_start=now,
        input_window_end=now,
        risk_level="high",
        confidence=0.62,
        recommended_action="pause_simulation",
        requires_human_confirmation=True,
        status="pending_human_confirmation",
        rationale="Elevated operational simulation score with low fusion confidence.",
        evidence_refs=["trace:trace-004"],
        contributing_signals=["emg"],
    )
    assert event.requires_human_confirmation is True
    assert event.risk_level == "high"
    data = event.model_dump(mode="json")
    assert data["schema_version"] == "v1"


def test_decision_event_invalid_confidence() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        DecisionEventV1(
            trace_id="trace-bad",
            source="axon-api",
            session_id="session-001",
            input_window_start=now,
            input_window_end=now,
            risk_level="low",
            confidence=1.5,
            recommended_action="continue_session",
            requires_human_confirmation=False,
            rationale="bad confidence",
        )


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
        source="axon-api",
        session_id="session-synthetic-001",
        agent_name="safety_agent",
        stage="completed",
        input_refs=["telemetry:emg"],
        output_summary="Safety verdict: pause_simulation, HITL=True",
        confidence=0.71,
        risk_level="high",
        tool_calls=["lookup_safety_policy"],
        llm_used=False,
        duration_ms=12.5,
    )
    assert event.agent_name == "safety_agent"
    data = event.model_dump(mode="json")
    assert "span_id" in data


def test_agent_trace_invalid_enum() -> None:
    with pytest.raises(ValidationError):
        AgentTraceEventV1(
            trace_id="trace-bad",
            source="axon-api",
            session_id="session-001",
            agent_name="not_a_real_agent",  # type: ignore[arg-type]
            stage="completed",
            output_summary="test",
        )


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
