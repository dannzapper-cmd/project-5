"""Artifact paths for Phase 7 checks (no imports from learning/ or RL modules)."""

from __future__ import annotations

from pathlib import Path

# Repo root: apps/api/app/reliability/paths.py -> parents[4]
ROOT = Path(__file__).resolve().parents[4]
ARTIFACTS = ROOT / "artifacts"

RELIABILITY_DIR = ARTIFACTS / "reliability"
OBSERVABILITY_DIR = ARTIFACTS / "observability"

FL_REPORT = ARTIFACTS / "learning" / "federated" / "federated_report.json"
FL_STATUS = ARTIFACTS / "learning" / "federated" / "status.json"
RL_REPORT = ARTIFACTS / "learning" / "rl" / "rl_report.json"
RL_STATUS = ARTIFACTS / "learning" / "rl" / "status.json"
MLOPS_REGISTRY = ARTIFACTS / "mlops" / "model_registry.json"
MLOPS_MLRUNS = ARTIFACTS / "mlops" / "mlruns"
