"""Preprocess SensorEventV1 into ONNX input vectors."""

from __future__ import annotations

import numpy as np

from apps.api.app.schemas.events import SensorEventV1

from edge_inference.model_registry import ModelMetadata


def _pad_values(values: list[float], size: int) -> list[float]:
    padded = list(values[:size])
    while len(padded) < size:
        padded.append(0.0)
    return padded


def preprocess_sensor_event(event: SensorEventV1, metadata: ModelMetadata) -> np.ndarray:
    """Build float32 input tensor from sensor event per model metadata shape."""
    signal_type = metadata.signal_type
    quality = float(event.quality)

    if signal_type == "emg":
        # [1, 8]: 5 signal samples + quality + node context + padding
        samples = _pad_values(event.values, 5)
        node_ctx = 0.0
        if event.metadata.get("node_id"):
            node_ctx = 0.1
        values = samples + [quality, node_ctx, 0.0]
    elif signal_type == "imu":
        # [1, 9]: 6 signal samples + quality + ax + ay
        samples = _pad_values(event.values, 6)
        ax = float(event.values[0]) if event.values else 0.0
        ay = float(event.values[1]) if len(event.values) > 1 else 0.0
        values = samples + [quality, ax, ay]
    else:
        raise ValueError(f"Unsupported signal_type for preprocessing: {signal_type}")

    expected = metadata.input_shape[1]
    values = _pad_values(values, expected)[:expected]
    data = np.array(values, dtype=np.float32).reshape(metadata.input_shape)
    assert data.dtype == np.float32
    return data
