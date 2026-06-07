"""Synthetic/replay dataset generation for simulated rehab sessions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np

from apps.mlops.config import (
    ALL_SCENARIOS,
    AXON_MLOPS_SMOKE,
    AXON_SMOKE_DATASET_ROWS,
    AXON_SMOKE_SCENARIOS,
    DATASETS_DIR,
    DEFAULT_SEED,
    GENERATOR_VERSION,
    SCENARIO_EMG_LABEL,
    SCENARIO_IMU_LABEL,
)
from apps.mlops.features import extract_emg_features, extract_imu_features


def _scenario_params(scenario: str, rng: np.random.Generator) -> dict:
    """Return signal generation parameters per scenario."""
    base = {"noise": 0.05, "amplitude": 1.0, "dropout_prob": 0.0}
    overrides = {
        "normal_session": {"noise": 0.03, "amplitude": 0.8},
        "fatigue_event": {"noise": 0.08, "amplitude": 0.5},
        "movement_spike": {"noise": 0.06, "amplitude": 2.5},
        "sensor_dropout": {"dropout_prob": 0.4, "noise": 0.02},
        "low_confidence_drift": {"noise": 0.15, "amplitude": 0.6},
        "multi_anomaly": {"noise": 0.12, "amplitude": 1.8, "dropout_prob": 0.2},
    }
    return {**base, **overrides.get(scenario, {})}


def _generate_emg_window(scenario: str, rng: np.random.Generator, size: int = 128) -> np.ndarray:
    params = _scenario_params(scenario, rng)
    t = np.linspace(0, 1, size)
    signal = params["amplitude"] * np.sin(2 * np.pi * 5 * t)
    signal += rng.normal(0, params["noise"], size)
    if params["dropout_prob"] > 0 and rng.random() < params["dropout_prob"]:
        mask = rng.random(size) > 0.5
        signal = signal * mask
    return signal.astype(np.float32)


def _generate_imu_window(scenario: str, rng: np.random.Generator, size: int = 64) -> np.ndarray:
    params = _scenario_params(scenario, rng)
    t = np.linspace(0, 1, size)
    axes = []
    for freq in (1.0, 1.5, 2.0):
        axis = params["amplitude"] * np.sin(2 * np.pi * freq * t)
        axis += rng.normal(0, params["noise"], size)
        axes.append(axis)
    window = np.stack(axes, axis=1).astype(np.float32)
    if scenario == "movement_spike" or scenario == "multi_anomaly":
        window[size // 2 :, :] *= 2.5
    if params["dropout_prob"] > 0 and rng.random() < params["dropout_prob"]:
        window[rng.integers(0, size, size // 4), :] = 0.0
    return window


def generate_synthetic_dataset(
    seed: int = DEFAULT_SEED,
    rows: int = 500,
    scenarios: list[str] | None = None,
) -> dict:
    """Generate deterministic synthetic dataset with features and raw windows."""
    if AXON_MLOPS_SMOKE:
        rows = min(rows, AXON_SMOKE_DATASET_ROWS)
        scenarios = (scenarios or ALL_SCENARIOS)[:AXON_SMOKE_SCENARIOS]
    else:
        scenarios = scenarios or ALL_SCENARIOS

    rng = np.random.default_rng(seed)
    dataset_id = f"synth-{seed}-{uuid4().hex[:8]}"
    emg_features: list[np.ndarray] = []
    imu_features: list[np.ndarray] = []
    emg_raw: list[np.ndarray] = []
    imu_raw: list[np.ndarray] = []
    emg_labels: list[str] = []
    imu_labels: list[str] = []
    row_scenarios: list[str] = []

    per_scenario = max(1, rows // len(scenarios))
    for scenario in scenarios:
        for _ in range(per_scenario):
            emg_w = _generate_emg_window(scenario, rng)
            imu_w = _generate_imu_window(scenario, rng)
            emg_features.append(extract_emg_features(emg_w))
            imu_features.append(extract_imu_features(imu_w))
            emg_raw.append(emg_w)
            imu_raw.append(imu_w)
            emg_labels.append(SCENARIO_EMG_LABEL[scenario])
            imu_labels.append(SCENARIO_IMU_LABEL[scenario])
            row_scenarios.append(scenario)

    return {
        "dataset_id": dataset_id,
        "seed": seed,
        "scenarios": scenarios,
        "row_count": len(row_scenarios),
        "emg": {
            "features": np.stack(emg_features),
            "raw_windows": emg_raw,
            "labels": emg_labels,
        },
        "imu": {
            "features": np.stack(imu_features),
            "raw_windows": imu_raw,
            "labels": imu_labels,
        },
        "row_scenarios": row_scenarios,
    }


def write_dataset_artifacts(dataset: dict, output_dir: Path | None = None) -> Path:
    """Persist dataset arrays and metadata to artifacts/mlops/datasets/."""
    dataset_id = dataset["dataset_id"]
    out = output_dir or (DATASETS_DIR / dataset_id)
    out.mkdir(parents=True, exist_ok=True)

    np.save(out / "emg_features.npy", dataset["emg"]["features"])
    np.save(out / "imu_features.npy", dataset["imu"]["features"])
    with open(out / "emg_labels.json", "w") as f:
        json.dump(dataset["emg"]["labels"], f)
    with open(out / "imu_labels.json", "w") as f:
        json.dump(dataset["imu"]["labels"], f)

    metadata = {
        "dataset_id": dataset_id,
        "created_at": datetime.now(UTC).isoformat(),
        "generator_version": GENERATOR_VERSION,
        "seed": dataset["seed"],
        "scenario": dataset["scenarios"],
        "signal_types": ["emg", "imu"],
        "row_count": dataset["row_count"],
        "synthetic_only": True,
        "prohibited_use_notes": (
            "Not for clinical use. Not for medical diagnosis. Not for treatment decisions."
        ),
    }
    with open(out / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    from apps.mlops.cards import write_data_card

    write_data_card(metadata, dataset, out / "data_card.md")
    return out
