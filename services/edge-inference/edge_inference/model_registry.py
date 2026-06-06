"""Load ONNX model metadata and registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelMetadata:
    """Companion metadata for an ONNX model artifact."""

    model_name: str
    model_version: str
    onnx_filename: str
    opset_version: int
    input_name: str
    input_shape: list[int]
    input_dtype: str
    output_names: list[str]
    signal_type: str
    labels: list[str]
    safety_note: str
    created_at: str

    @classmethod
    def from_json(cls, data: dict) -> ModelMetadata:
        return cls(
            model_name=data["model_name"],
            model_version=data["model_version"],
            onnx_filename=data["onnx_filename"],
            opset_version=data["opset_version"],
            input_name=data["input_name"],
            input_shape=data["input_shape"],
            input_dtype=data["input_dtype"],
            output_names=data["output_names"],
            signal_type=data["signal_type"],
            labels=data["labels"],
            safety_note=data["safety_note"],
            created_at=data["created_at"],
        )


class ModelRegistry:
    """Registry of signal_type -> model metadata and paths."""

    def __init__(self, model_dir: str, metadata_dir: str) -> None:
        self.model_dir = Path(model_dir)
        self.metadata_dir = Path(metadata_dir)
        self._models: dict[str, tuple[ModelMetadata, Path]] = {}
        self._load_all()

    def _load_all(self) -> None:
        for meta_path in sorted(self.metadata_dir.glob("*.json")):
            data = json.loads(meta_path.read_text())
            meta = ModelMetadata.from_json(data)
            onnx_path = self.model_dir / meta.onnx_filename
            if not onnx_path.exists():
                raise FileNotFoundError(f"ONNX file missing: {onnx_path}")
            self._models[meta.signal_type] = (meta, onnx_path)

    def get_for_signal(self, signal_type: str) -> tuple[ModelMetadata, Path] | None:
        return self._models.get(signal_type)

    def supported_signals(self) -> list[str]:
        return list(self._models.keys())
