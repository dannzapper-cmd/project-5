"""Phase 6A federated learning REST routes.

Exposes the latest on-demand federated run to the dashboard. These endpoints are
read-only mirrors of the artifacts written by ``apps.learning.federated.runner``;
they never start training (no always-on process — item 13).

  - GET /api/learning/federated/status   compact status (idle before any run)
  - GET /api/learning/federated/latest    full latest result + convergence curve
  - GET /api/learning/federated/history   recent run summaries

Synthetic federated learning simulation. No real patient data. No medical claims.
"""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.app.learning.service import (
    get_federated_result,
    get_federated_status,
    get_history,
)
from apps.api.app.schemas.learning import FederatedResultV1, FederatedStatusV1

router = APIRouter(prefix="/api/learning/federated", tags=["learning"])


@router.get("/status", response_model=FederatedStatusV1)
def federated_status() -> FederatedStatusV1:
    """Latest federated run status (idle/null metrics before any run)."""
    return get_federated_status()


@router.get("/latest", response_model=FederatedResultV1)
def federated_latest() -> FederatedResultV1:
    """Full latest federated result including the convergence curve."""
    return get_federated_result()


@router.get("/history")
def federated_history(limit: int = 20) -> dict:
    """Recent federated run summaries (most recent first)."""
    return get_history(limit=limit)
