"""Phase 2 edge AI tests (no Docker/Redis/MQTT required)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from apps.api.app.schemas.events import ModelScoreEventV1, SensorEventV1
from apps.api.app.telemetry.model_score_streams import MODEL_SCORE_STREAM
from apps.api.app.telemetry.redis_streams import model_score_to_ws_message
from scripts.generate_phase2_models import generate_emg_model, generate_imu_model

from edge_inference.model_registry import ModelMetadata, ModelRegistry
from edge_inference.onnx_runner import OnnxRunner
from edge_inference.preprocess import preprocess_sensor_event
from edge_inference.scoring import build_model_score_event

PROHIBITED_LABELS = [
    "arrhythmia",
    "hypoxia",
    "tachycardia",
    "bradycardia",
    "diagnosis",
    "clinical",
    "disease",
    "pathology",
    "cardiac",
    "oxygen deficiency",
    "fatigue syndrome",
]


@pytest.fixture
def emg_model(tmp_path: Path) -> str:
    model_dir = tmp_path / "onnx"
    meta_dir = tmp_path / "metadata"
    model_dir.mkdir()
    meta_dir.mkdir()
    generate_emg_model(model_dir / "emg_anomaly_v0.onnx", metadata_dir=meta_dir)
    return str(model_dir / "emg_anomaly_v0.onnx")


@pytest.fixture
def imu_model(tmp_path: Path) -> str:
    model_dir = tmp_path / "onnx"
    meta_dir = tmp_path / "metadata"
    model_dir.mkdir()
    meta_dir.mkdir()
    generate_imu_model(model_dir / "imu_movement_v0.onnx", metadata_dir=meta_dir)
    return str(model_dir / "imu_movement_v0.onnx")


@pytest.fixture
def emg_metadata() -> ModelMetadata:
    return ModelMetadata(
        model_name="emg_anomaly",
        model_version="v0",
        onnx_filename="emg_anomaly_v0.onnx",
        opset_version=13,
        input_name="input",
        input_shape=[1, 8],
        input_dtype="float32",
        output_names=["score", "label_idx"],
        signal_type="emg",
        labels=["normal", "elevated_activity"],
        safety_note="Synthetic operational score only. Not medical.",
        created_at="2026-01-01T00:00:00+00:00",
    )


def test_generate_emg_model_valid(emg_model: str) -> None:
    import onnx

    model = onnx.load(emg_model)
    onnx.checker.check_model(model)


def test_generate_imu_model_valid(imu_model: str) -> None:
    import onnx

    model = onnx.load(imu_model)
    onnx.checker.check_model(model)


def test_onnx_runner_loads_and_infers(emg_model: str, emg_metadata: ModelMetadata) -> None:
    runner = OnnxRunner(emg_metadata, emg_model)
    input_data = np.zeros((1, 8), dtype=np.float32)
    result = runner.run(input_data)
    assert 0.0 <= result.score <= 1.0
    assert result.label in ["normal", "elevated_activity"]
    assert result.latency_ms >= 0


def test_onnx_runner_requires_float32(emg_model: str, emg_metadata: ModelMetadata) -> None:
    runner = OnnxRunner(emg_metadata, emg_model)
    input_data = np.zeros((1, 8), dtype=np.float64)
    with pytest.raises(AssertionError, match="float32"):
        runner.run(input_data)


def test_model_score_event_v1_validates() -> None:
    event = ModelScoreEventV1(
        trace_id="trace-test",
        source="edge-inference",
        model_name="emg_anomaly",
        model_version="v0",
        score=0.42,
        confidence=0.88,
        latency_ms=3.5,
        input_event_id="sensor-evt-1",
        output_label="normal",
        metadata={"signal_type": "emg", "input_signal": "emg"},
    )
    assert event.output_label == "normal"


def test_model_score_stream_name() -> None:
    assert MODEL_SCORE_STREAM == "axon:v1:stream:model_scores"


def test_model_score_ws_payload_serialization() -> None:
    event = ModelScoreEventV1(
        trace_id="trace-ws",
        source="edge-inference",
        model_name="imu_movement",
        model_version="v0",
        score=0.55,
        confidence=0.9,
        latency_ms=2.1,
        input_event_id="sensor-evt-2",
        output_label="stable_motion",
        metadata={"input_signal": "imu"},
    )
    msg = model_score_to_ws_message(event)
    assert msg["type"] == "model_score"
    assert msg["event"]["model_name"] == "imu_movement"


def test_scoring_builds_model_score_event(emg_metadata: ModelMetadata) -> None:
    from edge_inference.onnx_runner import InferenceResult

    sensor = SensorEventV1(
        trace_id="trace-score",
        source="sensor-emg",
        signal_type="emg",
        unit="mV",
        values=[0.1, 0.2, 0.15, 0.12, 0.11],
        quality=0.95,
    )
    inference = InferenceResult(score=0.3, label_idx=0, label="normal", latency_ms=1.5)
    score_event = build_model_score_event(sensor, emg_metadata, inference, "edge-inference")
    assert score_event.model_name == "emg_anomaly"
    assert score_event.output_label == "normal"


def test_preprocess_emg_shape(emg_metadata: ModelMetadata) -> None:
    sensor = SensorEventV1(
        trace_id="trace-pre",
        source="sensor-emg",
        signal_type="emg",
        unit="mV",
        values=[0.1, 0.2, 0.15],
        quality=0.9,
        metadata={"node_id": "emg-01"},
    )
    arr = preprocess_sensor_event(sensor, emg_metadata)
    assert arr.shape == (1, 8)
    assert arr.dtype == np.float32


def test_benchmark_returns_p50_p95(tmp_path: Path) -> None:
    from scripts.benchmark_inference import benchmark_model

    model_dir = tmp_path / "onnx"
    meta_dir = tmp_path / "metadata"
    model_dir.mkdir()
    meta_dir.mkdir()
    onnx_path = model_dir / "emg_anomaly_v0.onnx"
    generate_emg_model(onnx_path, metadata_dir=meta_dir)
    metadata = json.loads((meta_dir / "emg_anomaly_v0.json").read_text())
    result = benchmark_model(onnx_path, metadata)
    assert result.p50_ms >= 0
    assert result.p95_ms >= 0
    assert result.total_runs == 200


def test_no_medical_labels_in_model_metadata() -> None:
    meta_dir = Path(__file__).resolve().parents[1] / "models" / "metadata"
    if not meta_dir.exists():
        pytest.skip("metadata not generated yet")
    for meta_file in meta_dir.glob("*.json"):
        content = json.loads(meta_file.read_text())
        for label in content["labels"]:
            for term in PROHIBITED_LABELS:
                assert term not in label.lower(), (
                    f"Prohibited medical term '{term}' found in label '{label}'"
                )


def test_model_registry_loads(tmp_path: Path) -> None:
    model_dir = tmp_path / "onnx"
    meta_dir = tmp_path / "metadata"
    model_dir.mkdir()
    meta_dir.mkdir()
    generate_emg_model(model_dir / "emg_anomaly_v0.onnx", metadata_dir=meta_dir)
    registry = ModelRegistry(str(model_dir), str(meta_dir))
    assert "emg" in registry.supported_signals()
