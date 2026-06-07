"""Train and export candidate v2 models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
from sklearn.model_selection import train_test_split

from apps.mlops.config import EMG_LABELS, IMU_LABELS, MODELS_DIR
from apps.mlops.export import export_candidate_to_onnx
from apps.mlops.model_builder import build_candidate_model
from apps.mlops.paths import assert_not_protected


def _labels_for_signal(signal_type: str) -> list[str]:
    return EMG_LABELS if signal_type == "emg" else IMU_LABELS


def train_and_export_candidate(
    signal_type: str,
    features: np.ndarray,
    labels: list[str],
    output_path: str | None = None,
    smoke: bool = False,
    seed: int = 42,
) -> str:
    """Train LogisticRegression candidate and export to ONNX."""
    label_set = _labels_for_signal(signal_type)
    y = np.array([label_set.index(lbl) for lbl in labels])
    X = features.astype(np.float32)

    test_size = 0.2 if len(X) >= 10 else 0.1
    stratify = y if len(set(y)) > 1 and len(y) >= 10 else None
    X_train, _, y_train, _ = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=stratify
    )

    pipeline = build_candidate_model()
    pipeline.fit(X_train, y_train)

    if output_path is None:
        output_path = str(MODELS_DIR / f"{signal_type}_v2_candidate.onnx")
    assert_not_protected(output_path)
    export_candidate_to_onnx(pipeline, n_features=X.shape[1], output_path=output_path)
    return output_path


def candidate_metadata(
    signal_type: str,
    artifact_path: str,
    dataset_id: str,
    metrics: dict,
) -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "model_id": str(uuid4()),
        "model_version": "v2_candidate",
        "signal_type": signal_type,
        "artifact_path": artifact_path,
        "created_at": now,
        "trained_on_dataset_id": dataset_id,
        "metrics": metrics,
        "safety_status": "candidate_under_review",
        "promotion_status": "candidate_not_promoted",
        "synthetic_only": True,
        "limitations": "Candidate model. Not promoted. Not for clinical use.",
        "approved_by": None,
        "approved_at": None,
        "notes": "",
    }
