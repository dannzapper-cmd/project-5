"""Scenario definitions for synthetic signal shaping (Phase 1)."""

from dataclasses import dataclass
from typing import Literal

ScenarioName = Literal[
    "normal_session",
    "fatigue_event",
    "sensor_dropout",
    "movement_spike",
    "multi_anomaly",
]

SCENARIOS: tuple[ScenarioName, ...] = (
    "normal_session",
    "fatigue_event",
    "sensor_dropout",
    "movement_spike",
    "multi_anomaly",
)


@dataclass(frozen=True)
class ScenarioProfile:
    """Adjustments applied per scenario (stream shape only, no AI decisions)."""

    name: ScenarioName
    quality_multiplier: float
    emg_burst_factor: float
    imu_spike_factor: float
    spo2_offset: float
    dropout_probability: float
    description: str


SCENARIO_PROFILES: dict[ScenarioName, ScenarioProfile] = {
    "normal_session": ScenarioProfile(
        name="normal_session",
        quality_multiplier=1.0,
        emg_burst_factor=1.0,
        imu_spike_factor=1.0,
        spo2_offset=0.0,
        dropout_probability=0.0,
        description="Baseline simulated rehab session telemetry.",
    ),
    "fatigue_event": ScenarioProfile(
        name="fatigue_event",
        quality_multiplier=0.60,
        emg_burst_factor=1.4,
        imu_spike_factor=0.7,
        spo2_offset=-2.0,
        dropout_probability=0.0,
        description="Elevated EMG variability and reduced motion quality.",
    ),
    "sensor_dropout": ScenarioProfile(
        name="sensor_dropout",
        quality_multiplier=0.5,
        emg_burst_factor=1.0,
        imu_spike_factor=1.0,
        spo2_offset=0.0,
        dropout_probability=0.35,
        description="Intermittent low-quality readings; no silent repair.",
    ),
    "movement_spike": ScenarioProfile(
        name="movement_spike",
        quality_multiplier=0.9,
        emg_burst_factor=1.2,
        imu_spike_factor=2.5,
        spo2_offset=0.0,
        dropout_probability=0.0,
        description="Sudden IMU movement spike during simulated exercise.",
    ),
    "multi_anomaly": ScenarioProfile(
        name="multi_anomaly",
        quality_multiplier=0.75,
        emg_burst_factor=1.6,
        imu_spike_factor=1.8,
        spo2_offset=-3.0,
        dropout_probability=0.15,
        description="Combined synthetic anomalies across multiple streams.",
    ),
}


def get_scenario(name: str) -> ScenarioProfile:
    """Return scenario profile or default to normal_session."""
    if name in SCENARIO_PROFILES:
        return SCENARIO_PROFILES[name]  # type: ignore[index]
    return SCENARIO_PROFILES["normal_session"]
