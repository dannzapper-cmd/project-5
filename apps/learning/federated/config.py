"""Phase 6A federated learning configuration, paths, and client registry.

All values are deterministic and CPU-friendly. The FL experiment is on-demand
only; importing this module has no side effects beyond defining constants.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root: apps/learning/federated/config.py -> parents[3] == repo root.
ROOT = Path(__file__).resolve().parents[3]

# Artifacts live alongside the Phase 4 MLOps artifacts but in their own subtree.
LEARNING_ARTIFACTS = ROOT / "artifacts" / "learning" / "federated"
RUNS_DIR = LEARNING_ARTIFACTS / "runs"
LATEST_REPORT_PATH = LEARNING_ARTIFACTS / "federated_report.json"
STATUS_PATH = LEARNING_ARTIFACTS / "status.json"
CLIENT_DISTRIBUTION_PATH = LEARNING_ARTIFACTS / "client_distribution_summary.json"
CONVERGENCE_JSON_PATH = LEARNING_ARTIFACTS / "convergence.json"
CONVERGENCE_CSV_PATH = LEARNING_ARTIFACTS / "convergence.csv"
MODEL_CARD_PATH = LEARNING_ARTIFACTS / "model_card_axon_fl_v1.md"

# MLflow defaults to a local file store so no server is ever required.
MLFLOW_DEFAULT_TRACKING_DIR = ROOT / "artifacts" / "mlops" / "mlruns"
MLFLOW_EXPERIMENT_NAME = "axon_federated_learning"

# Reproducibility (item 7 of the Phase 6A guardrails).
DEFAULT_SEED = int(os.getenv("FL_SEED", "42"))

# Feature contract for AxonFLModelV1 (item 6). Order matters — the model and the
# synthetic generator share this exact ordering.
FEATURE_NAMES: tuple[str, ...] = (
    "emg_mean",
    "emg_variance",
    "ecg_mean",
    "ecg_variance",
    "imu_magnitude",
    "imu_variance",
    "spo2_mean",
    "spo2_missing_ratio",
)
INPUT_DIM = len(FEATURE_NAMES)
HIDDEN_LAYERS: tuple[int, ...] = (32, 16)
OUTPUT_DIM = 2  # 0 = normal, 1 = anomaly
CLASS_NAMES = ("normal", "anomaly")
MODEL_TYPE = "AxonFLModelV1"

# Default (non-test) experiment parameters — produce meaningful convergence.
DEFAULT_NUM_ROUNDS = 5
DEFAULT_LOCAL_EPOCHS = 3
DEFAULT_LEARNING_RATE = 0.05
DEFAULT_DATASET_SIZE = 300  # samples per client

# Sentinel for a "missing" SpO2 reading represented safely (item 8).
SPO2_MISSING_SENTINEL = -1.0


# --- Synthetic edge client registry (item 8) ------------------------------
# Each client has a statistically distinct, non-IID distribution. ``signal_focus``
# documents the dominant synthetic anomaly pattern. ``anomaly_ratio`` controls the
# class balance. ``data_size`` slightly varies per client (federated realism).
#
# SYNTHETIC ONLY — no real patient data, no clinical datasets, no medical claims.
CLIENT_REGISTRY: tuple[dict, ...] = (
    {
        "client_id": "edge-client-01",
        "client_index": 1,
        "signal_type": "emg_fatigue_noise",
        "description": "EMG-heavy fatigue/noise pattern (high variance, occasional spikes).",
        "anomaly_ratio": 0.40,
        "data_size": 320,
    },
    {
        "client_id": "edge-client-02",
        "client_index": 2,
        "signal_type": "ecg_drift_spike",
        "description": "ECG-like drift/spike pattern (lower variance, linear drift).",
        "anomaly_ratio": 0.35,
        "data_size": 300,
    },
    {
        "client_id": "edge-client-03",
        "client_index": 3,
        "signal_type": "imu_movement_dropout",
        "description": "IMU movement spike/dropout pattern (bimodal, dropout events).",
        "anomaly_ratio": 0.45,
        "data_size": 280,
    },
    {
        "client_id": "edge-client-04",
        "client_index": 4,
        "signal_type": "spo2_low_missing",
        "description": "SpO2-proxy low-signal/missing-reading pattern (missing ratio feature).",
        "anomaly_ratio": 0.38,
        "data_size": 260,
    },
    {
        "client_id": "edge-client-05",
        "client_index": 5,
        "signal_type": "mixed_multi_anomaly",
        "description": "Mixed multi-anomaly pattern across EMG/ECG/IMU/SpO2 proxies.",
        "anomaly_ratio": 0.42,
        "data_size": 300,
    },
)

# Documented production minimum (default runs use 3-5 clients). The technical
# floor is 2 (FedAvg needs >= 2 participants) and is only used by tiny test
# fixtures; real/default experiments always use >= MIN_CLIENTS.
MIN_CLIENTS = 3
ABS_MIN_CLIENTS = 2
MAX_CLIENTS = len(CLIENT_REGISTRY)


def client_specs(num_clients: int) -> list[dict]:
    """Return the first ``num_clients`` client specs (clamped to the registry)."""
    if num_clients < ABS_MIN_CLIENTS:
        raise ValueError(f"num_clients must be >= {ABS_MIN_CLIENTS}")
    if num_clients > MAX_CLIENTS:
        raise ValueError(f"num_clients must be <= {MAX_CLIENTS}")
    return [dict(spec) for spec in CLIENT_REGISTRY[:num_clients]]
