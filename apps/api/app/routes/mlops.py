"""Phase 4 MLOps API routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from apps.api.app.mlops.state import mlops_state
from apps.mlops.config import (
    LATEST_EVAL_PATH,
    MLOPS_ARTIFACTS,
    REGISTRY_PATH,
)
from apps.mlops.promotion import promote_candidate
from apps.mlops.registry import ensure_registry, load_registry

router = APIRouter(prefix="/api/v1/mlops", tags=["mlops"])

SAFETY_NOTICE = (
    "Synthetic simulation only. No medical diagnosis. No treatment advice. No clinical claims."
)


class PromoteCandidateRequest(BaseModel):
    signal_type: Literal["emg", "imu"]
    dry_run: bool = True
    confirm_manual_promotion: bool = False
    operator_note: str = ""


class PromoteCandidateResponse(BaseModel):
    dry_run: bool
    signal_type: str
    candidate_path: str
    active_path: str
    would_overwrite: bool
    promotion_status: str
    safety_notice: str
    review_record_id: str
    timestamp: str


def _safe_read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


@router.get("/status")
def mlops_status() -> dict:
    """Aggregate MLOps status for dashboard polling."""
    registry = load_registry() if REGISTRY_PATH.exists() else ensure_registry()
    latest_eval = _safe_read_json(LATEST_EVAL_PATH)

    active_emg = registry.get("active_models", {}).get("emg", {})
    active_imu = registry.get("active_models", {}).get("imu", {})
    cand_emg = registry.get("candidate_models", {}).get("emg", {})
    cand_imu = registry.get("candidate_models", {}).get("imu", {})

    return {
        "phase": "Phase 4 - MLOps + Synthetic Retraining",
        "active_model_version": {
            "emg": active_emg.get("model_version", "v1"),
            "imu": active_imu.get("model_version", "v1"),
        },
        "candidate_model_version": {
            "emg": cand_emg.get("model_version", "none"),
            "imu": cand_imu.get("model_version", "none"),
        },
        "candidate_promotion_status": {
            "emg": cand_emg.get("promotion_status", "no_candidate"),
            "imu": cand_imu.get("promotion_status", "no_candidate"),
        },
        "latest_eval": latest_eval,
        "drift": {
            "status": mlops_state.drift_status,
            "score": mlops_state.drift_score,
            "recommendation": mlops_state.drift_recommendation,
            "last_check_at": mlops_state.last_drift_check_at,
        },
        "last_eval_at": latest_eval.get("created_at") if latest_eval else mlops_state.last_eval_at,
        "artifact_paths": {
            "registry": str(REGISTRY_PATH),
            "latest_eval": str(LATEST_EVAL_PATH),
            "artifacts_root": str(MLOPS_ARTIFACTS),
        },
        "data_card_summary": "Synthetic replay datasets in artifacts/mlops/datasets/",
        "model_card_summary": "Candidate model cards in artifacts/mlops/evals/",
        "safety_notice": SAFETY_NOTICE,
        "has_eval_run": latest_eval is not None,
    }


@router.get("/latest-eval")
def latest_eval() -> dict:
    data = _safe_read_json(LATEST_EVAL_PATH)
    if data is None:
        return {
            "status": "empty",
            "message": "No evaluation run yet",
            "synthetic_only": True,
            "safety_notice": SAFETY_NOTICE,
        }
    return data


@router.get("/model-registry")
def model_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return ensure_registry()
    return load_registry()


@router.get("/artifacts")
def list_artifacts() -> dict:
    root = MLOPS_ARTIFACTS
    if not root.exists():
        return {"artifacts": [], "safety_notice": SAFETY_NOTICE}
    paths = []
    for p in root.rglob("*"):
        if p.is_file() and p.name != ".gitkeep":
            paths.append(str(p.relative_to(root)))
    return {"artifacts": sorted(paths)[:100], "safety_notice": SAFETY_NOTICE}


@router.post("/promote-candidate", response_model=PromoteCandidateResponse)
def promote_candidate_endpoint(body: PromoteCandidateRequest) -> PromoteCandidateResponse:
    result = promote_candidate(
        signal_type=body.signal_type,
        dry_run=body.dry_run,
        confirm_manual_promotion=body.confirm_manual_promotion,
        operator_note=body.operator_note,
    )
    return PromoteCandidateResponse(
        dry_run=result["dry_run"],
        signal_type=result["signal_type"],
        candidate_path=result.get("candidate_path", ""),
        active_path=result.get("active_path", ""),
        would_overwrite=result.get("would_overwrite", False),
        promotion_status=result.get("promotion_status", "unknown"),
        safety_notice=result.get("safety_notice", ""),
        review_record_id=result.get("review_record_id", ""),
        timestamp=result.get("timestamp", datetime.now(UTC).isoformat()),
    )
