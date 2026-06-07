"""Export candidate sklearn pipeline to ONNX (opset 13)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import onnxruntime as rt
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.pipeline import Pipeline

from apps.mlops.paths import assert_not_protected


def export_candidate_to_onnx(
    pipeline: Pipeline,
    n_features: int,
    output_path: str,
) -> None:
    assert_not_protected(output_path)
    initial_type = [("float_input", FloatTensorType([None, n_features]))]
    onnx_model = convert_sklearn(
        pipeline,
        initial_types=initial_type,
        target_opset=13,
    )
    with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as f:
        f.write(onnx_model.SerializeToString())
        tmp = f.name
    try:
        sess = rt.InferenceSession(tmp)
        assert sess is not None
    finally:
        os.unlink(tmp)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    assert_not_protected(output_path)
    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
