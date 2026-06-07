"""In-process MLOps / drift state for API status."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MlopsState:
    drift_status: str = "insufficient_data"
    drift_score: float | None = None
    drift_recommendation: str = "continue_monitoring"
    last_drift_check_at: str | None = None
    last_eval_at: str | None = None
    last_drift_event_id: str | None = None


mlops_state = MlopsState()
