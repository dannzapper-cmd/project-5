"""Tests for MQTT topic routing and Redis stream mapping."""

from apps.api.app.telemetry.topic_router import (
    ALL_STREAMS,
    MQTT_SUBSCRIBE_TOPICS,
    TOPIC_TO_SIGNAL_TYPE,
    TOPIC_TO_STREAM,
    match_topic_prefix,
    signal_type_for_topic,
    stream_for_topic,
)


def test_explicit_topic_to_stream_mapping() -> None:
    assert TOPIC_TO_STREAM["axon/v1/sensors/emg"] == "axon:v1:stream:sensors:emg"
    assert TOPIC_TO_STREAM["axon/v1/sensors/ecg-like"] == "axon:v1:stream:sensors:ecg_like"
    assert TOPIC_TO_STREAM["axon/v1/sensors/imu"] == "axon:v1:stream:sensors:imu"
    assert TOPIC_TO_STREAM["axon/v1/sensors/spo2-proxy"] == "axon:v1:stream:sensors:spo2_proxy"
    assert TOPIC_TO_STREAM["axon/v1/robot/state"] == "axon:v1:stream:robot_state"


def test_hyphen_underscore_signal_type_mapping() -> None:
    assert TOPIC_TO_SIGNAL_TYPE["axon/v1/sensors/ecg-like"] == "ecg_like"
    assert TOPIC_TO_SIGNAL_TYPE["axon/v1/sensors/spo2-proxy"] == "spo2_proxy"


def test_stream_for_topic_with_node_suffix() -> None:
    topic = "axon/v1/sensors/emg/rehab-node-01"
    assert stream_for_topic(topic) == "axon:v1:stream:sensors:emg"
    assert signal_type_for_topic(topic) == "emg"


def test_stream_for_robot_state_topic() -> None:
    topic = "axon/v1/robot/state/rehab-robot-01"
    assert stream_for_topic(topic) == "axon:v1:stream:robot_state"
    assert signal_type_for_topic(topic) == "robot_state"


def test_unknown_topic_returns_none() -> None:
    assert match_topic_prefix("axon/v1/unknown/x") is None
    assert stream_for_topic("axon/v1/unknown/x") is None


def test_mqtt_subscribe_topics_defined() -> None:
    assert len(MQTT_SUBSCRIBE_TOPICS) == 5
    assert "axon/v1/sensors/ecg-like/+" in MQTT_SUBSCRIBE_TOPICS


def test_all_streams_count() -> None:
    assert len(ALL_STREAMS) == 5
