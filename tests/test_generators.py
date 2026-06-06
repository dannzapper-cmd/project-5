"""Tests for synthetic sensor generators."""

import random

import pytest
from apps.api.app.schemas.events import SensorEventV1
from pydantic import ValidationError

from axon_generators.config import GeneratorConfig
from axon_generators.generator import build_sensor_event, generate_event_batch
from axon_generators.scenarios import SCENARIOS, get_scenario
from axon_generators.signals import MQTT_TOPIC_TEMPLATES


def test_generator_returns_valid_sensor_event_v1() -> None:
    profile = get_scenario("normal_session")
    rng = random.Random(42)
    event = build_sensor_event(
        "emg",
        tick=1,
        profile=profile,
        rng=rng,
        trace_id="test-trace",
        source="test-generator",
        node_id="node-01",
        robot_id="robot-01",
    )
    assert isinstance(event, SensorEventV1)
    assert event.signal_type == "emg"
    assert event.values


def test_scenario_names_are_supported() -> None:
    assert "normal_session" in SCENARIOS
    assert "fatigue_event" in SCENARIOS
    assert "sensor_dropout" in SCENARIOS
    assert "movement_spike" in SCENARIOS
    assert "multi_anomaly" in SCENARIOS
    for name in SCENARIOS:
        profile = get_scenario(name)
        assert profile.name == name


def test_generate_event_batch_has_five_streams() -> None:
    config = GeneratorConfig(axon_seed=7)
    batch = generate_event_batch(config, tick=0, seed=7)
    assert len(batch) == 5
    signal_types = {event.signal_type for _, event in batch}
    assert signal_types == {"emg", "ecg_like", "imu", "spo2_proxy", "robot_state"}


def test_mqtt_topic_templates_match_taxonomy() -> None:
    assert MQTT_TOPIC_TEMPLATES["emg"] == "axon/v1/sensors/emg/{node_id}"
    assert MQTT_TOPIC_TEMPLATES["ecg_like"] == "axon/v1/sensors/ecg-like/{node_id}"
    assert MQTT_TOPIC_TEMPLATES["spo2_proxy"] == "axon/v1/sensors/spo2-proxy/{node_id}"
    assert MQTT_TOPIC_TEMPLATES["robot_state"] == "axon/v1/robot/state/{robot_id}"


def test_robot_state_event_validates() -> None:
    profile = get_scenario("normal_session")
    rng = random.Random(1)
    event = build_sensor_event(
        "robot_state",
        tick=3,
        profile=profile,
        rng=rng,
        trace_id="trace-robot",
        source="gen",
        node_id="n1",
        robot_id="r1",
    )
    assert event.unit == "state"
    assert len(event.values) == 4


def test_invalid_quality_fails_validation() -> None:
    with pytest.raises(ValidationError):
        SensorEventV1(
            trace_id="t",
            source="s",
            signal_type="emg",
            unit="mV",
            values=[0.1],
            quality=1.5,
        )
