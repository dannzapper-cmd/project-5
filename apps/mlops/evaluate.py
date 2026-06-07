"""Offline evaluation: Phase 2 v1 vs candidate v2."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import onnxruntime as rt
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from apps.api.app.schemas.events import SensorEventV1
from apps.mlops.cards import write_model_card
from apps.mlops.config import (
    EMG_LABELS,
    IMU_LABELS,
    LATEST_EVAL_PATH,
    MLOPS_ARTIFACTS,
    MODELS_DIR,
    PHASE2_METADATA_DIR,
    PHASE2_ONNX_DIR,
    SAFETY_NOTES,
)
from apps.mlops.dataset import generate_synthetic_dataset, write_dataset_artifacts
from apps.mlops.registry import update_candidate_in_registry, write_registry_atomic
from apps.mlops.train import candidate_metadata, train_and_export_candidate
from edge_inference.model_registry import ModelRegistry
from edge_inference.onnx_runner import OnnxRunner
from edge_inference.preprocess import preprocess_sensor_event

V1_EMG_MAP = {"normal": "normal", "elevated_activity": "anomaly"}
V1_IMU_MAP = {"stable_motion": "normal", "movement_spike": "spike"}


def _parse_onnx_class_output(outputs: list, output_names: list[str], n_classes: int) -> int:
    """Parse sklearn ONNX classifier outputs to class index."""
    for out, name in zip(outputs, output_names, strict=False):
        name_lower = name.lower()
        if "label" in name_lower:
            return int(out.flatten()[0])
        if "prob" in name_lower:
            return int(np.argmax(out))
    if len(outputs) >= 2:
        second = outputs[1]
        if hasattr(second, "shape") and len(second.shape) >= 1:
            flat = np.asarray(second).flatten()
            if flat.size >= n_classes:
                return int(np.argmax(flat[:n_classes]))
    return int(np.argmax(np.asarray(outputs[0]).flatten()))


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    arr = np.array(values)
    return float(np.percentile(arr, p))


def _evaluate_v1_onnx(
    signal_type: str,
    raw_windows: list,
    ground_labels: list[str],
    label_set: list[str],
) -> dict:
    """Evaluate Phase 2 ONNX model on raw windows."""
    meta_dir = PHASE2_METADATA_DIR
    onnx_dir = PHASE2_ONNX_DIR
    if not meta_dir.exists() or not onnx_dir.exists():
        from scripts.generate_phase2_models import generate_all

        generate_all()

    registry = ModelRegistry(str(onnx_dir), str(meta_dir))
    pair = registry.get_for_signal(signal_type)
    if pair is None:
        raise FileNotFoundError(f"No Phase 2 model for {signal_type}")
    meta, onnx_path = pair
    runner = OnnxRunner(meta, str(onnx_path))

    preds: list[str] = []
    latencies: list[float] = []
    label_map = V1_EMG_MAP if signal_type == "emg" else V1_IMU_MAP

    for window in raw_windows:
        if signal_type == "emg":
            values = window.tolist()[:5]
        else:
            values = window[:, 0].tolist()[:6]
        event = SensorEventV1(
            trace_id="eval-v1",
            source="mlops-eval",
            signal_type=signal_type,
            unit="mV" if signal_type == "emg" else "g",
            values=values,
            quality=0.9,
            metadata={"node_id": "eval-node"},
        )
        inp = preprocess_sensor_event(event, meta)
        result = runner.run(inp)
        latencies.append(result.latency_ms)
        mapped = label_map.get(result.label, result.label)
        preds.append(mapped)

    y_true = ground_labels
    y_pred = preds
    cm = confusion_matrix(y_true, y_pred, labels=label_set).tolist()
    return {
        "model_path": str(onnx_path.resolve()),
        "model_version": "v1",
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(
            precision_score(y_true, y_pred, labels=label_set, average="macro", zero_division=0)
        ),
        "recall_macro": float(
            recall_score(y_true, y_pred, labels=label_set, average="macro", zero_division=0)
        ),
        "f1_macro": float(
            f1_score(y_true, y_pred, labels=label_set, average="macro", zero_division=0)
        ),
        "confusion_matrix": cm,
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
    }


def _evaluate_v2_onnx(
    model_path: str,
    features: np.ndarray,
    labels: list[str],
    label_set: list[str],
) -> dict:
    """Evaluate candidate v2 ONNX on feature vectors."""
    sess = rt.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    output_names = [o.name for o in sess.get_outputs()]
    preds: list[str] = []
    latencies: list[float] = []

    for row in features:
        inp = row.reshape(1, -1).astype(np.float32)
        t0 = time.perf_counter()
        outputs = sess.run(output_names, {input_name: inp})
        latencies.append((time.perf_counter() - t0) * 1000)
        idx = _parse_onnx_class_output(outputs, output_names, len(label_set))
        preds.append(label_set[idx])

    y_true = labels
    y_pred = preds
    cm = confusion_matrix(y_true, y_pred, labels=label_set).tolist()
    return {
        "model_path": model_path,
        "model_version": "v2_candidate",
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(
            precision_score(y_true, y_pred, labels=label_set, average="macro", zero_division=0)
        ),
        "recall_macro": float(
            recall_score(y_true, y_pred, labels=label_set, average="macro", zero_division=0)
        ),
        "f1_macro": float(
            f1_score(y_true, y_pred, labels=label_set, average="macro", zero_division=0)
        ),
        "confusion_matrix": cm,
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
    }


def _improvement_recommendation(v1: dict, v2: dict) -> str:
    acc_delta = v2["accuracy"] - v1["accuracy"]
    f1_delta = v2["f1_macro"] - v1["f1_macro"]
    if acc_delta > 0.05 and f1_delta > 0.05:
        return "promote_candidate"
    if acc_delta < -0.05:
        return "keep_current"
    return "insufficient_data"


def run_evaluation_pipeline(
    signal_type: str = "emg",
    smoke: bool = False,
    seed: int = 42,
) -> dict:
    """Full eval pipeline for one signal type."""
    dataset = generate_synthetic_dataset(seed=seed, rows=200 if not smoke else 50)
    write_dataset_artifacts(dataset)

    data = dataset[signal_type]
    features = data["features"]
    labels = data["labels"]
    raw = data["raw_windows"]
    label_set = EMG_LABELS if signal_type == "emg" else IMU_LABELS

    _, X_test, _, y_test, _, raw_test = _split_test(features, labels, raw, seed)
    _, _, _, y_train_raw, _, _ = _split_test(features, labels, raw, seed)

    candidate_path = str(MODELS_DIR / f"{signal_type}_v2_candidate.onnx")
    train_and_export_candidate(
        signal_type,
        features,
        labels,
        output_path=candidate_path,
        smoke=smoke,
        seed=seed,
    )

    v1 = _evaluate_v1_onnx(signal_type, raw_test, y_test, label_set)
    v2 = _evaluate_v2_onnx(candidate_path, X_test, y_test, label_set)

    acc_delta = v2["accuracy"] - v1["accuracy"]
    f1_delta = v2["f1_macro"] - v1["f1_macro"]
    lat_delta = v2["latency_p95_ms"] - v1["latency_p95_ms"]

    report = {
        "eval_id": str(uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
        "dataset_id": dataset["dataset_id"],
        "seed": seed,
        "synthetic_only": True,
        "safety_notes": SAFETY_NOTES,
        "signal_type": signal_type,
        "v1": v1,
        "v2_candidate": v2,
        "improvement": {
            "accuracy_delta": acc_delta,
            "f1_macro_delta": f1_delta,
            "latency_p95_delta_ms": lat_delta,
            "recommendation": _improvement_recommendation(v1, v2),
        },
    }

    eval_dir = MLOPS_ARTIFACTS / "evals" / report["eval_id"]
    eval_dir.mkdir(parents=True, exist_ok=True)
    write_registry_atomic(report, eval_dir / "eval_report.json")
    write_registry_atomic(report, LATEST_EVAL_PATH)

    md_lines = [
        f"# Eval Report: {report['eval_id']}",
        "",
        f"- Signal: {signal_type}",
        f"- Dataset: {dataset['dataset_id']}",
        f"- Recommendation: {report['improvement']['recommendation']}",
        "",
        "## v1 vs v2",
        "| Metric | v1 | v2_candidate |",
        "|--------|-----|--------------|",
        f"| Accuracy | {v1['accuracy']:.4f} | {v2['accuracy']:.4f} |",
        f"| F1-macro | {v1['f1_macro']:.4f} | {v2['f1_macro']:.4f} |",
        f"| Latency p95 ms | {v1['latency_p95_ms']:.4f} | {v2['latency_p95_ms']:.4f} |",
        "",
        SAFETY_NOTES,
    ]
    (eval_dir / "eval_report.md").write_text("\n".join(md_lines))

    write_model_card(
        signal_type,
        "v2_candidate",
        dataset["dataset_id"],
        v2,
        "candidate_not_promoted",
        "LogisticRegression Pipeline",
        eval_dir / f"model_card_{signal_type}_v2_candidate.md",
    )

    meta = candidate_metadata(signal_type, candidate_path, dataset["dataset_id"], v2)
    update_candidate_in_registry(signal_type, meta)

    return report


def _split_test(features, labels, raw, seed):
    idx = np.arange(len(labels))
    stratify = labels if len(set(labels)) > 1 and len(labels) >= 10 else None
    train_idx, test_idx = train_test_split(
        idx,
        test_size=0.2,
        random_state=seed,
        stratify=stratify,
    )
    return (
        features[train_idx],
        features[test_idx],
        [labels[i] for i in train_idx],
        [labels[i] for i in test_idx],
        [raw[i] for i in train_idx],
        [raw[i] for i in test_idx],
    )


def run_full_pipeline(smoke: bool = False, seed: int = 42) -> dict:
    """Run eval for both EMG and IMU."""
    reports = {}
    for sig in ("emg", "imu"):
        reports[sig] = run_evaluation_pipeline(signal_type=sig, smoke=smoke, seed=seed)
    return reports
