"""MLOps configuration and smoke-mode limits."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MLOPS_ARTIFACTS = ROOT / "artifacts" / "mlops"
DATASETS_DIR = MLOPS_ARTIFACTS / "datasets"
MODELS_DIR = MLOPS_ARTIFACTS / "models"
PROMOTION_REVIEWS_DIR = MLOPS_ARTIFACTS / "promotion_reviews"
REGISTRY_PATH = MLOPS_ARTIFACTS / "model_registry.json"
LATEST_EVAL_PATH = MLOPS_ARTIFACTS / "latest_eval.json"

PHASE2_ONNX_DIR = ROOT / "models" / "onnx"
PHASE2_METADATA_DIR = ROOT / "models" / "metadata"

GENERATOR_VERSION = "axon-mlops-v1"
DEFAULT_SEED = 42

EMG_LABELS = ["normal", "fatigue", "anomaly"]
IMU_LABELS = ["normal", "spike", "dropout"]

ALL_SCENARIOS = [
    "normal_session",
    "fatigue_event",
    "movement_spike",
    "sensor_dropout",
    "low_confidence_drift",
    "multi_anomaly",
]

SCENARIO_EMG_LABEL = {
    "normal_session": "normal",
    "fatigue_event": "fatigue",
    "movement_spike": "anomaly",
    "sensor_dropout": "anomaly",
    "low_confidence_drift": "fatigue",
    "multi_anomaly": "anomaly",
}

SCENARIO_IMU_LABEL = {
    "normal_session": "normal",
    "fatigue_event": "normal",
    "movement_spike": "spike",
    "sensor_dropout": "dropout",
    "low_confidence_drift": "normal",
    "multi_anomaly": "spike",
}

AXON_MLOPS_BACKEND = os.getenv("AXON_MLOPS_BACKEND", "local")
AXON_MLOPS_SMOKE = os.getenv("AXON_MLOPS_SMOKE", "").lower() in ("1", "true", "yes")
AXON_SMOKE_DATASET_ROWS = int(os.getenv("AXON_SMOKE_DATASET_ROWS", "100"))
AXON_SMOKE_SCENARIOS = int(os.getenv("AXON_SMOKE_SCENARIOS", "3"))

DRIFT_WINDOW = int(os.getenv("AXON_DRIFT_WINDOW_SIZE", "20"))
DRIFT_THRESHOLD = float(os.getenv("AXON_DRIFT_CONFIDENCE_THRESHOLD", "0.60"))
DRIFT_CHECK_INTERVAL = int(os.getenv("AXON_DRIFT_CHECK_INTERVAL_SECONDS", "30"))

DRIFT_STREAM = "axon:v1:stream:drift_events"

SAFETY_NOTES = (
    "Evaluation on synthetic signals only. No clinical inference."
)
