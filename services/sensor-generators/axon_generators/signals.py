"""Synthetic signal value generators (not medically accurate)."""

import math
import random
from typing import Literal

from axon_generators.scenarios import ScenarioProfile

SignalKind = Literal["emg", "ecg_like", "imu", "spo2_proxy", "robot_state"]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate_emg_values(rng: random.Random, tick: int, profile: ScenarioProfile) -> list[float]:
    """Short EMG-like burst window with mild noise."""
    base = 0.05 + 0.02 * math.sin(tick / 5.0)
    burst = profile.emg_burst_factor * (0.3 if tick % 7 < 3 else 0.08)
    return [
        round(base + burst + rng.uniform(-0.02, 0.02), 4),
        round(base + burst * 0.9 + rng.uniform(-0.015, 0.015), 4),
        round(base + burst * 0.8 + rng.uniform(-0.01, 0.01), 4),
    ]


def generate_ecg_like_values(
    rng: random.Random, tick: int, _profile: ScenarioProfile
) -> list[float]:
    """Repeated waveform-like values; synthetic only."""
    phase = tick % 10
    template = [0.1, 0.3, 1.0, 0.2, -0.1, 0.05, 0.1, 0.15, 0.1, 0.08]
    values = [template[(phase + i) % len(template)] for i in range(5)]
    return [round(v + rng.uniform(-0.03, 0.03), 4) for v in values]


def generate_imu_values(rng: random.Random, tick: int, profile: ScenarioProfile) -> list[float]:
    """Compact IMU vector: ax, ay, az, gx, gy, gz (synthetic)."""
    spike = profile.imu_spike_factor if tick % 11 == 0 else 1.0
    return [
        round(rng.uniform(-0.2, 0.2) * spike, 4),
        round(rng.uniform(-0.2, 0.2) * spike, 4),
        round(1.0 + rng.uniform(-0.05, 0.05), 4),
        round(rng.uniform(-0.1, 0.1) * spike, 4),
        round(rng.uniform(-0.1, 0.1) * spike, 4),
        round(rng.uniform(-0.05, 0.05), 4),
    ]


def generate_spo2_proxy_values(
    rng: random.Random, tick: int, profile: ScenarioProfile
) -> list[float]:
    """SpO2-proxy synthetic percentage; not pulse oximetry."""
    base = 97.0 + profile.spo2_offset + 0.5 * math.sin(tick / 8.0)
    return [round(_clamp(base + rng.uniform(-0.4, 0.4), 90.0, 100.0), 2)]


def generate_robot_state_values(
    rng: random.Random, tick: int, _profile: ScenarioProfile
) -> list[float]:
    """Robot state: battery_pct, joint_angle_deg, load_pct, mode_code."""
    battery = _clamp(88.0 - tick * 0.01 + rng.uniform(-0.2, 0.2), 10.0, 100.0)
    joint = 30.0 + 10.0 * math.sin(tick / 6.0) + rng.uniform(-1.0, 1.0)
    load = _clamp(40.0 + 15.0 * abs(math.sin(tick / 4.0)), 0.0, 100.0)
    mode = 1.0 if tick % 20 < 15 else 2.0  # 1=active, 2=rest
    return [round(battery, 2), round(joint, 2), round(load, 2), mode]


def compute_quality(rng: random.Random, profile: ScenarioProfile) -> float:
    """Quality score with scenario adjustments and optional dropout."""
    if rng.random() < profile.dropout_probability:
        return round(rng.uniform(0.15, 0.45), 3)
    base = rng.uniform(0.88, 0.99) * profile.quality_multiplier
    return round(_clamp(base, 0.0, 1.0), 3)


SIGNAL_UNITS: dict[SignalKind, str] = {
    "emg": "mV",
    "ecg_like": "mV",
    "imu": "g/rad_s",
    "spo2_proxy": "%",
    "robot_state": "state",
}

SIGNAL_GENERATORS = {
    "emg": generate_emg_values,
    "ecg_like": generate_ecg_like_values,
    "imu": generate_imu_values,
    "spo2_proxy": generate_spo2_proxy_values,
    "robot_state": generate_robot_state_values,
}

MQTT_TOPIC_TEMPLATES: dict[SignalKind, str] = {
    "emg": "axon/v1/sensors/emg/{node_id}",
    "ecg_like": "axon/v1/sensors/ecg-like/{node_id}",
    "imu": "axon/v1/sensors/imu/{node_id}",
    "spo2_proxy": "axon/v1/sensors/spo2-proxy/{node_id}",
    "robot_state": "axon/v1/robot/state/{robot_id}",
}
