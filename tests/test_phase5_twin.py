"""Phase 5 Digital Twin and command tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from apps.api.app.schemas.twin import (
    AgentStateV1,
    DigitalTwinStateV1,
    FusionStateV1,
    RobotStateV1,
    ROS2BridgeStatusV1,
    SafetyStateV1,
    SensorNodeStateV1,
    TwinCommandRequestV1,
)
from apps.api.app.twin import service as twin_service


@pytest.fixture(autouse=True)
def _reset_twin_command_state() -> None:
    twin_service._session_paused = False
    twin_service._safety_stop_active = False
    twin_service._assist_mode = "assist_medium"


def _sample_sensor_nodes(
    emg_status: str = "active",
    emg_updated: datetime | None = None,
) -> dict:
    now = datetime.now(UTC)
    ts = emg_updated or now
    return {
        "emg": SensorNodeStateV1(
            status=emg_status,  # type: ignore[arg-type]
            latest_value_summary="0.12",
            confidence=0.9,
            last_updated=ts,
        ),
        "ecg": SensorNodeStateV1(
            status="active",
            latest_value_summary="72",
            confidence=0.88,
            last_updated=now,
        ),
        "imu": SensorNodeStateV1(
            status="active",
            latest_value_summary="0.1",
            confidence=0.85,
            last_updated=now,
        ),
        "spo2": SensorNodeStateV1(
            status="active",
            latest_value_summary="98",
            confidence=0.92,
            last_updated=now,
        ),
    }


def test_digital_twin_state_v1_schema_serializes() -> None:
    now = datetime.now(UTC)
    state = DigitalTwinStateV1(
        robot_id="rehab-robot-01",
        session_id="session-001",
        timestamp=now,
        robot_state=RobotStateV1(mode="assisting"),
        sensor_nodes=_sample_sensor_nodes(),
        fusion=FusionStateV1(global_confidence=0.87, risk_level="nominal"),
        agents=AgentStateV1(),
        safety=SafetyStateV1(),
        ros2_bridge=ROS2BridgeStatusV1(),
    )
    data = state.model_dump(mode="json")
    assert data["schema_version"] == "v1"
    assert data["robot_id"] == "rehab-robot-01"
    assert "emg" in data["sensor_nodes"]


def test_sensor_stale_transition() -> None:
    now = datetime.now(UTC)
    stale_ts = now - timedelta(seconds=twin_service.SENSOR_STALE_TTL_SECONDS + 1)
    status = twin_service._sensor_status(stale_ts, 0.9, now)
    assert status == "stale"


def test_sensor_dropout_transition() -> None:
    now = datetime.now(UTC)
    dropout_ts = now - timedelta(seconds=twin_service.SENSOR_DROPOUT_TTL_SECONDS + 1)
    status = twin_service._sensor_status(dropout_ts, 0.9, now)
    assert status == "dropout"


def test_robot_mode_degrades_on_low_confidence_and_stale_sensor() -> None:
    nodes = _sample_sensor_nodes(emg_status="stale")
    mode = twin_service._derive_robot_mode(0.35, nodes, "low", None)
    assert mode == "degraded"


def test_robot_mode_degrades_on_dropout_even_with_high_confidence() -> None:
    nodes = _sample_sensor_nodes(emg_status="dropout")
    mode = twin_service._derive_robot_mode(0.95, nodes, "medium", None)
    assert mode == "degraded"


def test_dropout_overrides_nominal_decision_risk() -> None:
    nodes = _sample_sensor_nodes(emg_status="dropout")
    risk = twin_service._derive_risk_level(
        0.95,
        nodes,
        {"risk_level": "nominal"},
        {"high_risk": False},
    )
    assert risk == "medium"


def test_stable_motion_model_label_is_nominal() -> None:
    assert "stable_motion" in twin_service.NOMINAL_MODEL_LABELS


def test_pause_command_accepted() -> None:
    twin_service._session_paused = False
    twin_service._safety_stop_active = False
    req = TwinCommandRequestV1(command="pause", requested_by="test-operator")
    resp = asyncio.run(twin_service.handle_twin_command(req))
    assert resp.status == "accepted"
    assert twin_service._session_paused is True
    assert resp.trace_id


def test_resume_blocked_when_safety_stop_active() -> None:
    twin_service._safety_stop_active = True
    twin_service._session_paused = True
    req = TwinCommandRequestV1(command="resume", requested_by="test-operator")
    resp = asyncio.run(twin_service.handle_twin_command(req))
    assert resp.status == "blocked"
    assert "safety stop" in (resp.reason or "").lower()


def test_safety_stop_accepted() -> None:
    twin_service._safety_stop_active = False
    req = TwinCommandRequestV1(
        command="request_safety_stop",
        requested_by="test-operator",
        reason="operator drill",
    )
    resp = asyncio.run(twin_service.handle_twin_command(req))
    assert resp.status in ("accepted", "pending_hitl")
    assert twin_service._safety_stop_active is True


def test_set_assist_mode_requires_mode() -> None:
    twin_service._safety_stop_active = False
    twin_service._session_paused = False
    req = TwinCommandRequestV1(command="set_assist_mode", requested_by="test-operator")
    resp = asyncio.run(twin_service.handle_twin_command(req))
    assert resp.status == "rejected"


def test_twin_broadcast_serialization() -> None:
    redis = AsyncMock()
    redis.xrevrange = AsyncMock(return_value=[])

    with patch.object(twin_service, "get_safety_status", return_value={"high_risk": False}):
        with patch.object(twin_service, "get_current_decision", return_value=None):
            with patch.object(twin_service, "get_recent_traces", return_value=[]):
                twin = asyncio.run(twin_service.build_twin_state(redis))
                msg = {"type": "twin_state", "state": twin.model_dump(mode="json")}
                assert msg["type"] == "twin_state"
                assert msg["state"]["schema_version"] == "v1"


def test_timing_env_defaults() -> None:
    assert 2 <= twin_service.TWIN_BROADCAST_HZ <= 10
    assert 3 <= twin_service.SENSOR_STALE_TTL_SECONDS <= 10
    assert 10 <= twin_service.SENSOR_DROPOUT_TTL_SECONDS <= 30
