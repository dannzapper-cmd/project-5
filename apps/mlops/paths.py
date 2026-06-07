"""Discover and protect Phase 2 active model paths."""

from __future__ import annotations

from pathlib import Path

from apps.mlops.config import PHASE2_METADATA_DIR, PHASE2_ONNX_DIR

PROTECTED_MODEL_PATHS: list[str] = []


def discover_protected_paths() -> list[str]:
    """Collect absolute paths of Phase 2 active ONNX artifacts."""
    paths: list[str] = []
    if PHASE2_ONNX_DIR.exists():
        for onnx in PHASE2_ONNX_DIR.glob("*.onnx"):
            paths.append(str(onnx.resolve()))
    return paths


def refresh_protected_paths() -> None:
    """Refresh module-level protected path list from disk."""
    global PROTECTED_MODEL_PATHS
    PROTECTED_MODEL_PATHS = discover_protected_paths()


def assert_not_protected(path: str) -> None:
    """Raise if Phase 4 attempts to write to a Phase 2 active model path."""
    if not PROTECTED_MODEL_PATHS:
        refresh_protected_paths()
    target = Path(path).resolve()
    for protected in PROTECTED_MODEL_PATHS:
        if target == Path(protected).resolve():
            raise RuntimeError(
                f"Phase 4 attempted to write to protected Phase 2 model path: {path}. "
                "Aborted. Active models are never modified by Phase 4."
            )


def get_phase2_model_path(signal_type: str) -> Path | None:
    """Resolve Phase 2 ONNX path for emg or imu from metadata."""
    meta_dir = PHASE2_METADATA_DIR
    if not meta_dir.exists():
        return None
    for meta_file in meta_dir.glob("*.json"):
        import json

        data = json.loads(meta_file.read_text())
        if data.get("signal_type") == signal_type:
            onnx_path = PHASE2_ONNX_DIR / data["onnx_filename"]
            if onnx_path.exists():
                return onnx_path.resolve()
    return None


refresh_protected_paths()
