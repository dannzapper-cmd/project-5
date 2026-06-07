"""Atomic model registry read/write."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from apps.mlops.config import REGISTRY_PATH
from apps.mlops.paths import get_phase2_model_path


def write_registry_atomic(registry: dict, path: str | Path) -> None:
    """Write registry JSON atomically via temp file + os.replace."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(registry, f, indent=2, default=str)
        os.replace(tmp_path, p)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_registry(path: Path | None = None) -> dict:
    """Load registry or return seeded default."""
    reg_path = path or REGISTRY_PATH
    if reg_path.exists():
        return json.loads(reg_path.read_text())
    return seed_initial_registry()


def seed_initial_registry() -> dict:
    """Build initial registry with Phase 2 active models."""
    now = datetime.now(UTC).isoformat()
    active: dict = {}
    for signal_type in ("emg", "imu"):
        artifact = get_phase2_model_path(signal_type)
        if artifact is None:
            continue
        active[signal_type] = {
            "model_id": str(uuid4()),
            "model_version": "v1",
            "signal_type": signal_type,
            "artifact_path": str(artifact),
            "created_at": now,
            "trained_on_dataset_id": "phase2_deterministic",
            "metrics": {},
            "safety_status": "approved_for_simulation",
            "promotion_status": "active",
            "synthetic_only": True,
            "limitations": "Deterministic synthetic model. Not for clinical use.",
            "approved_by": "phase2_automated",
            "approved_at": now,
            "notes": "",
        }
    return {
        "last_updated": now,
        "active_models": active,
        "candidate_models": {},
    }


def ensure_registry() -> dict:
    """Ensure registry file exists on disk."""
    registry = load_registry()
    write_registry_atomic(registry, REGISTRY_PATH)
    return registry


def update_candidate_in_registry(
    signal_type: str,
    candidate_meta: dict,
    registry_path: Path | None = None,
) -> dict:
    """Update candidate_models entry and persist."""
    registry = load_registry(registry_path)
    registry["candidate_models"][signal_type] = candidate_meta
    registry["last_updated"] = datetime.now(UTC).isoformat()
    write_registry_atomic(registry, registry_path or REGISTRY_PATH)
    return registry
