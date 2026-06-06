"""Tests for WebSocket payload serialization."""

import random

from apps.api.app.telemetry.mqtt_client import channel_for_signal, event_to_ws_message

from axon_generators.generator import build_sensor_event
from axon_generators.scenarios import get_scenario


def test_websocket_payload_serialization() -> None:
    profile = get_scenario("normal_session")
    event = build_sensor_event(
        "imu",
        tick=0,
        profile=profile,
        rng=random.Random(0),
        trace_id="ws-trace",
        source="test",
        node_id="n1",
        robot_id="r1",
    )
    message = event_to_ws_message(event)
    assert message["type"] == "event"
    assert message["event"]["signal_type"] == "imu"
    assert "timestamp" in message["event"]


def test_channel_for_signal_types() -> None:
    assert channel_for_signal("emg") == "sensors"
    assert channel_for_signal("robot_state") == "robot-state"
