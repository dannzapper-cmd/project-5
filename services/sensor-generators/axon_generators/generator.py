"""Build SensorEventV1 payloads for synthetic telemetry."""

import random
from typing import Any

from apps.api.app.schemas.events import SensorEventV1

from axon_generators.config import GeneratorConfig
from axon_generators.scenarios import ScenarioProfile, get_scenario
from axon_generators.signals import (
    SIGNAL_GENERATORS,
    SIGNAL_UNITS,
    SignalKind,
    compute_quality,
)


def build_sensor_event(
    signal_type: SignalKind,
    *,
    tick: int,
    profile: ScenarioProfile,
    rng: random.Random,
    trace_id: str,
    source: str,
    node_id: str,
    robot_id: str,
    mode: str = "synthetic",
) -> SensorEventV1:
    """Create one validated SensorEventV1 for the given signal type."""
    generator = SIGNAL_GENERATORS[signal_type]
    values = generator(rng, tick, profile)
    entity_id = robot_id if signal_type == "robot_state" else node_id
    metadata: dict[str, Any] = {
        "scenario": profile.name,
        "mode": mode,
        "entity_id": entity_id,
        "tick": tick,
    }
    return SensorEventV1(
        trace_id=trace_id,
        source=source,
        signal_type=signal_type,
        unit=SIGNAL_UNITS[signal_type],
        values=values,
        quality=compute_quality(rng, profile),
        metadata=metadata,
    )


def generate_event_batch(
    config: GeneratorConfig,
    tick: int,
    *,
    mode: str = "synthetic",
    scenario_name: str | None = None,
    seed: int | None = None,
) -> list[tuple[str, SensorEventV1]]:
    """Generate one event per stream with MQTT topic."""
    profile = get_scenario(scenario_name or config.scenario)
    effective_seed = seed if seed is not None else (config.axon_seed or tick)
    rng = random.Random(effective_seed + tick)

    signal_types: list[SignalKind] = ["emg", "ecg_like", "imu", "spo2_proxy", "robot_state"]
    from axon_generators.signals import MQTT_TOPIC_TEMPLATES

    results: list[tuple[str, SensorEventV1]] = []
    for signal_type in signal_types:
        event = build_sensor_event(
            signal_type,
            tick=tick,
            profile=profile,
            rng=rng,
            trace_id=config.axon_trace_id,
            source=config.axon_source,
            node_id=config.axon_node_id,
            robot_id=config.axon_robot_id,
            mode=mode,
        )
        if signal_type == "robot_state":
            topic = MQTT_TOPIC_TEMPLATES[signal_type].format(robot_id=config.axon_robot_id)
        else:
            topic = MQTT_TOPIC_TEMPLATES[signal_type].format(node_id=config.axon_node_id)
        results.append((topic, event))
    return results
