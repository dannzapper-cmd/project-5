"""MQTT topic prefix to Redis stream and signal_type mapping."""

TOPIC_TO_STREAM: dict[str, str] = {
    "axon/v1/sensors/emg": "axon:v1:stream:sensors:emg",
    "axon/v1/sensors/ecg-like": "axon:v1:stream:sensors:ecg_like",
    "axon/v1/sensors/imu": "axon:v1:stream:sensors:imu",
    "axon/v1/sensors/spo2-proxy": "axon:v1:stream:sensors:spo2_proxy",
    "axon/v1/robot/state": "axon:v1:stream:robot_state",
}

TOPIC_TO_SIGNAL_TYPE: dict[str, str] = {
    "axon/v1/sensors/emg": "emg",
    "axon/v1/sensors/ecg-like": "ecg_like",
    "axon/v1/sensors/imu": "imu",
    "axon/v1/sensors/spo2-proxy": "spo2_proxy",
    "axon/v1/robot/state": "robot_state",
}

MQTT_SUBSCRIBE_TOPICS: list[str] = [
    "axon/v1/sensors/emg/+",
    "axon/v1/sensors/ecg-like/+",
    "axon/v1/sensors/imu/+",
    "axon/v1/sensors/spo2-proxy/+",
    "axon/v1/robot/state/+",
]

SENSOR_STREAMS: list[str] = [
    "axon:v1:stream:sensors:emg",
    "axon:v1:stream:sensors:ecg_like",
    "axon:v1:stream:sensors:imu",
    "axon:v1:stream:sensors:spo2_proxy",
]

ROBOT_STREAM: str = "axon:v1:stream:robot_state"

ALL_STREAMS: list[str] = SENSOR_STREAMS + [ROBOT_STREAM]


def match_topic_prefix(topic: str) -> str | None:
    """Match full MQTT topic to configured prefix (before node/robot id suffix)."""
    for prefix in TOPIC_TO_STREAM:
        if topic.startswith(prefix + "/") or topic == prefix:
            return prefix
    return None


def stream_for_topic(topic: str) -> str | None:
    """Resolve Redis stream name from MQTT topic."""
    prefix = match_topic_prefix(topic)
    if prefix is None:
        return None
    return TOPIC_TO_STREAM[prefix]


def signal_type_for_topic(topic: str) -> str | None:
    """Resolve expected signal_type from MQTT topic prefix."""
    prefix = match_topic_prefix(topic)
    if prefix is None:
        return None
    return TOPIC_TO_SIGNAL_TYPE[prefix]
