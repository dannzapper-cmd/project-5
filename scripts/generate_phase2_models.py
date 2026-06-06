#!/usr/bin/env python3
"""Generate tiny deterministic ONNX models for Phase 2 edge inference."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from onnx import TensorProto, checker, helper, save

ROOT = Path(__file__).resolve().parents[1]
ONNX_DIR = ROOT / "models" / "onnx"
METADATA_DIR = ROOT / "models" / "metadata"

OPSET_VERSION = 13
IR_VERSION = 7


def _build_score_graph(
    input_shape: list[int],
    weights: np.ndarray,
    bias: float,
) -> helper.GraphProto:
    """Build graph: MatMul -> Add -> Sigmoid -> score; Greater -> Cast -> label_idx."""
    input_name = "input"
    w_name = "W"
    b_name = "B"
    matmul_out = "matmul_out"
    add_out = "add_out"
    score_name = "score"
    threshold_name = "threshold"
    greater_out = "greater_out"
    label_idx_name = "label_idx"

    feature_dim = input_shape[1]
    # MatMul: [1, feature_dim] x [feature_dim, 1] -> [1, 1]
    w_matrix = weights.reshape(feature_dim, 1).astype(np.float32)
    w_init = helper.make_tensor(
        w_name, TensorProto.FLOAT, [feature_dim, 1], w_matrix.flatten().tolist()
    )
    b_init = helper.make_tensor(b_name, TensorProto.FLOAT, [1], [bias])
    threshold_init = helper.make_tensor(threshold_name, TensorProto.FLOAT, [1], [0.5])

    input_tensor = helper.make_tensor_value_info(input_name, TensorProto.FLOAT, input_shape)
    score_tensor = helper.make_tensor_value_info(score_name, TensorProto.FLOAT, [1, 1])
    label_idx_tensor = helper.make_tensor_value_info(label_idx_name, TensorProto.FLOAT, [1, 1])

    nodes = [
        helper.make_node("MatMul", [input_name, w_name], [matmul_out]),
        helper.make_node("Add", [matmul_out, b_name], [add_out]),
        helper.make_node("Sigmoid", [add_out], [score_name]),
        helper.make_node("Greater", [score_name, threshold_name], [greater_out]),
        helper.make_node("Cast", [greater_out], [label_idx_name], to=TensorProto.FLOAT),
    ]

    graph = helper.make_graph(
        nodes,
        "score_graph",
        [input_tensor],
        [score_tensor, label_idx_tensor],
        initializer=[w_init, b_init, threshold_init],
    )
    return graph


def _save_model(
    graph: helper.GraphProto,
    output_path: Path,
    model_name: str,
) -> None:
    model = helper.make_model(
        graph,
        producer_name="axon-phase2",
        opset_imports=[helper.make_opsetid("", OPSET_VERSION)],
    )
    model.ir_version = IR_VERSION
    checker.check_model(model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save(model, str(output_path))
    print(f"Model {model_name} is valid.")


def _write_metadata(metadata: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2) + "\n")


def generate_emg_model(
    output_path: str | Path | None = None,
    metadata_dir: str | Path | None = None,
) -> Path:
    """Generate emg_anomaly_v0.onnx with [1, 8] float32 input."""
    weights = np.array(
        [[0.12, 0.18, 0.15, 0.10, 0.08, 0.25, 0.12, 0.0]],
        dtype=np.float32,
    )
    graph = _build_score_graph([1, 8], weights, bias=-0.45)
    path = Path(output_path) if output_path else ONNX_DIR / "emg_anomaly_v0.onnx"
    _save_model(graph, path, "emg_anomaly_v0")

    metadata = {
        "model_name": "emg_anomaly",
        "model_version": "v0",
        "onnx_filename": "emg_anomaly_v0.onnx",
        "opset_version": OPSET_VERSION,
        "input_name": "input",
        "input_shape": [1, 8],
        "input_dtype": "float32",
        "output_names": ["score", "label_idx"],
        "signal_type": "emg",
        "labels": ["normal", "elevated_activity"],
        "safety_note": "Synthetic operational score only. Not medical.",
        "created_at": datetime.now(UTC).isoformat(),
    }
    meta_dir = Path(metadata_dir) if metadata_dir else METADATA_DIR
    _write_metadata(metadata, meta_dir / "emg_anomaly_v0.json")
    return path


def generate_imu_model(
    output_path: str | Path | None = None,
    metadata_dir: str | Path | None = None,
) -> Path:
    """Generate imu_movement_v0.onnx with [1, 9] float32 input."""
    weights = np.array(
        [[0.10, 0.12, 0.08, 0.15, 0.14, 0.06, 0.20, 0.18, 0.07]],
        dtype=np.float32,
    )
    graph = _build_score_graph([1, 9], weights, bias=-0.40)
    path = Path(output_path) if output_path else ONNX_DIR / "imu_movement_v0.onnx"
    _save_model(graph, path, "imu_movement_v0")

    metadata = {
        "model_name": "imu_movement",
        "model_version": "v0",
        "onnx_filename": "imu_movement_v0.onnx",
        "opset_version": OPSET_VERSION,
        "input_name": "input",
        "input_shape": [1, 9],
        "input_dtype": "float32",
        "output_names": ["score", "label_idx"],
        "signal_type": "imu",
        "labels": ["stable_motion", "movement_spike"],
        "safety_note": "Synthetic operational score only. Not medical.",
        "created_at": datetime.now(UTC).isoformat(),
    }
    meta_dir = Path(metadata_dir) if metadata_dir else METADATA_DIR
    _write_metadata(metadata, meta_dir / "imu_movement_v0.json")
    return path


def generate_all() -> None:
    """Generate all Phase 2 ONNX models and metadata."""
    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    generate_emg_model()
    generate_imu_model()
    print(f"Generated models in {ONNX_DIR}")


def main() -> None:
    try:
        generate_all()
    except Exception as exc:
        print(f"ERROR: Model generation failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
