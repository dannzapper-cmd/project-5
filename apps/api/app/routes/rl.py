"""Phase 6B RL micro-module REST routes.

Exposes the latest on-demand RL run to the dashboard. These endpoints are
read-only mirrors of the artifacts written by ``apps.learning.rl.runner``; they
never start training (no always-on process — item 13) and never import
gymnasium / Stable-Baselines3 / torch (the core API stays lightweight).

  - GET /api/learning/rl/status   compact status (idle before any run)
  - GET /api/learning/rl/latest    full latest result + reward curve
  - GET /api/learning/rl/history   recent run summaries

Synthetic RL operational policy. No real patient data. No medical decisions.
Human review required for high-risk actions.
"""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.app.learning.rl_service import (
    get_rl_history,
    get_rl_result,
    get_rl_status,
)
from apps.api.app.schemas.rl import RLResultV1, RLStatusV1

router = APIRouter(prefix="/api/learning/rl", tags=["learning", "rl"])


@router.get("/status", response_model=RLStatusV1)
def rl_status() -> RLStatusV1:
    """Latest RL run status (idle/null metrics before any run)."""
    return get_rl_status()


@router.get("/latest", response_model=RLResultV1)
def rl_latest() -> RLResultV1:
    """Full latest RL result including the training reward curve."""
    return get_rl_result()


@router.get("/history")
def rl_history(limit: int = 20) -> dict:
    """Recent RL run summaries (most recent first)."""
    return get_rl_history(limit=limit)
