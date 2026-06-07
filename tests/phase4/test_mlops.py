"""Phase 4 MLOps tests — deterministic, offline, no Redis/MLflow."""

from __future__ import annotations

import json

import numpy as np
import onnxruntime
import pytest
from apps.api.main import app
from apps.mlops.backend import get_mlops_backend
from apps.mlops.dataset import generate_synthetic_dataset
from apps.mlops.drift import SlidingWindowDriftDetector
from apps.mlops.evaluate import run_evaluation_pipeline
from apps.mlops.features import extract_emg_features, extract_imu_features
from apps.mlops.paths import PROTECTED_MODEL_PATHS, assert_not_protected, refresh_protected_paths
from apps.mlops.promotion import promote_candidate_dry_run
from apps.mlops.registry import write_registry_atomic
from apps.mlops.train import train_and_export_candidate
from fastapi.testclient import TestClient
from scripts.generate_phase2_models import generate_emg_model


@pytest.fixture
def client():
    return TestClient(app)


def test_dataset_generator_deterministic():
    d1 = generate_synthetic_dataset(seed=42, rows=50, scenarios=["normal_session"])
    d2 = generate_synthetic_dataset(seed=42, rows=50, scenarios=["normal_session"])
    np.testing.assert_array_equal(d1["emg"]["features"], d2["emg"]["features"])


def test_emg_feature_extraction_shape():
    window = np.random.randn(128).astype(np.float32)
    feats = extract_emg_features(window)
    assert feats.shape == (5,)
    assert feats.dtype == np.float32


def test_imu_feature_extraction_shape():
    window = np.random.randn(64, 3).astype(np.float32)
    feats = extract_imu_features(window)
    assert feats.shape == (5,)
    assert feats.dtype == np.float32


def test_eval_report_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("AXON_MLOPS_SMOKE", "true")
    model_dir = tmp_path / "onnx"
    meta_dir = tmp_path / "metadata"
    model_dir.mkdir()
    meta_dir.mkdir()
    generate_emg_model(model_dir / "emg_anomaly_v0.onnx", metadata_dir=meta_dir)
    from scripts.generate_phase2_models import generate_imu_model

    generate_imu_model(model_dir / "imu_movement_v0.onnx", metadata_dir=meta_dir)
    monkeypatch.setattr("apps.mlops.paths.PHASE2_ONNX_DIR", model_dir)
    monkeypatch.setattr("apps.mlops.paths.PHASE2_METADATA_DIR", meta_dir)
    monkeypatch.setattr("apps.mlops.config.PHASE2_ONNX_DIR", model_dir)
    monkeypatch.setattr("apps.mlops.config.PHASE2_METADATA_DIR", meta_dir)
    monkeypatch.setattr("apps.mlops.config.MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr("apps.mlops.config.MLOPS_ARTIFACTS", tmp_path / "mlops")
    monkeypatch.setattr("apps.mlops.config.DATASETS_DIR", tmp_path / "mlops" / "datasets")
    eval_path = tmp_path / "mlops" / "latest_eval.json"
    reg_path = tmp_path / "mlops" / "model_registry.json"
    monkeypatch.setattr("apps.mlops.config.LATEST_EVAL_PATH", eval_path)
    monkeypatch.setattr("apps.mlops.config.REGISTRY_PATH", reg_path)
    refresh_protected_paths()

    report = run_evaluation_pipeline(signal_type="emg", smoke=True, seed=42)
    for key in ["eval_id", "v1", "v2_candidate", "improvement", "synthetic_only"]:
        assert key in report
    assert report["synthetic_only"] is True
    for metric in ["accuracy", "f1_macro", "latency_p50_ms", "latency_p95_ms"]:
        assert metric in report["v1"]
        assert metric in report["v2_candidate"]


def test_candidate_onnx_loadable(tmp_path, monkeypatch):
    monkeypatch.setenv("AXON_MLOPS_SMOKE", "true")
    ds = generate_synthetic_dataset(seed=42, rows=30, scenarios=["normal_session", "fatigue_event"])
    model_path = str(tmp_path / "emg_v2_candidate.onnx")
    train_and_export_candidate(
        "emg",
        ds["emg"]["features"],
        ds["emg"]["labels"],
        output_path=model_path,
        smoke=True,
        seed=42,
    )
    sess = onnxruntime.InferenceSession(model_path)
    dummy = np.zeros((1, 5), dtype=np.float32)
    outputs = sess.run(None, {sess.get_inputs()[0].name: dummy})
    assert outputs is not None


def test_phase2_active_model_path_protected(tmp_path, monkeypatch):
    model_dir = tmp_path / "onnx"
    meta_dir = tmp_path / "metadata"
    model_dir.mkdir()
    meta_dir.mkdir()
    path = model_dir / "emg_anomaly_v0.onnx"
    generate_emg_model(path, metadata_dir=meta_dir)
    monkeypatch.setattr("apps.mlops.paths.PHASE2_ONNX_DIR", model_dir)
    refresh_protected_paths()
    assert PROTECTED_MODEL_PATHS
    with pytest.raises(RuntimeError, match="protected Phase 2 model path"):
        assert_not_protected(str(path))


def test_promotion_dry_run_does_not_modify_files(tmp_path, monkeypatch):
    reg_path = tmp_path / "registry.json"
    cand_path = tmp_path / "candidate.onnx"
    cand_path.write_bytes(b"fake-onnx")
    registry = {
        "last_updated": "2026-01-01",
        "active_models": {
            "emg": {
                "artifact_path": str(tmp_path / "active.onnx"),
                "model_version": "v1",
            }
        },
        "candidate_models": {
            "emg": {
                "artifact_path": str(cand_path),
                "promotion_status": "candidate_not_promoted",
            }
        },
    }
    reg_path.write_text(json.dumps(registry))
    monkeypatch.setattr("apps.mlops.promotion.PROMOTION_REVIEWS_DIR", tmp_path / "reviews")
    monkeypatch.setattr("apps.mlops.registry.REGISTRY_PATH", reg_path)
    response = promote_candidate_dry_run("emg")
    assert response["dry_run"] is True
    assert "No automatic deployment" in response["safety_notice"]
    assert not (tmp_path / "active.onnx").exists()


def test_registry_atomic_write(tmp_path):
    registry = {"test": True}
    write_registry_atomic(registry, str(tmp_path / "registry.json"))
    with open(tmp_path / "registry.json") as f:
        loaded = json.load(f)
    assert loaded["test"] is True


def test_drift_detector_insufficient_data():
    detector = SlidingWindowDriftDetector(window=20, threshold=0.60)
    for _ in range(5):
        detector.update(0.4)
    result = detector.check()
    assert result["drift_status"] == "insufficient_data"


def test_drift_detector_detects_drift():
    detector = SlidingWindowDriftDetector(window=5, threshold=0.60)
    for _ in range(5):
        detector.update(0.35)
    result = detector.check()
    assert result["drift_status"] == "drift_detected"
    assert result["recommendation"] == "evaluate_candidate_model"


def test_drift_detector_nominal():
    detector = SlidingWindowDriftDetector(window=5, threshold=0.60)
    for _ in range(5):
        detector.update(0.95)
    result = detector.check()
    assert result["drift_status"] == "nominal"


def test_local_backend_runs_without_mlflow(tmp_path, monkeypatch):
    monkeypatch.setenv("AXON_MLOPS_BACKEND", "local")
    backend = get_mlops_backend(str(tmp_path / "run"))
    backend.log_params({"seed": 42})
    backend.log_metrics({"accuracy": 0.85})
    backend.end_run()
    assert (tmp_path / "run" / "params.json").exists()


def test_api_mlops_status_empty_state(client):
    response = client.get("/api/v1/mlops/status")
    assert response.status_code == 200
    data = response.json()
    assert "active_model_version" in data
    assert "candidate_promotion_status" in data
    assert "synthetic" in data.get("safety_notice", "").lower()


def test_drift_event_schema():
    from apps.api.app.schemas.events import DriftEventV1

    event = DriftEventV1(
        trace_id="t1",
        source="drift_detector",
        session_id="sess-1",
        signal_type="emg",
        threshold=0.6,
        drift_status="nominal",
        evidence_window=20,
        recommendation="continue_monitoring",
    )
    assert event.synthetic_only is True
