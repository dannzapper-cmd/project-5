"""ONNX Runtime inference runner."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import onnxruntime as ort

from edge_inference.model_registry import ModelMetadata


@dataclass
class InferenceResult:
    """Single inference output."""

    score: float
    label_idx: int
    label: str
    latency_ms: float


class OnnxRunner:
    """Load and run one ONNX model using metadata as single source of truth."""

    def __init__(self, metadata: ModelMetadata, onnx_path: str) -> None:
        self.metadata = metadata
        self.session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self.input_name = metadata.input_name
        self.output_names = metadata.output_names

    def run(self, input_array: np.ndarray) -> InferenceResult:
        assert input_array.dtype == np.float32, (
            f"Input dtype must be float32, got {input_array.dtype}"
        )
        expected_shape = tuple(self.metadata.input_shape)
        if input_array.shape != expected_shape:
            input_array = input_array.reshape(expected_shape)

        t0 = time.perf_counter()
        outputs = self.session.run(None, {self.input_name: input_array})
        latency_ms = (time.perf_counter() - t0) * 1000

        score = float(outputs[0].flatten()[0])
        label_idx = int(round(float(outputs[1].flatten()[0])))
        label_idx = max(0, min(label_idx, len(self.metadata.labels) - 1))
        label = self.metadata.labels[label_idx]
        score = max(0.0, min(1.0, score))

        return InferenceResult(
            score=score,
            label_idx=label_idx,
            label=label,
            latency_ms=latency_ms,
        )
