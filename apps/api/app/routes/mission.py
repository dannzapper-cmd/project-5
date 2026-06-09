"""Phase 8 mission control API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.app.mission.evidence_index import build_evidence_index
from apps.api.app.mission.scenarios import list_scenarios, run_scenario
from apps.api.app.mission.status import build_mission_status
from apps.api.app.mission.timeline import build_mission_timeline

router = APIRouter(prefix="/mission", tags=["mission"])


class ScenarioRunRequest(BaseModel):
    scenario: str = Field(..., description="Scenario name to run")


def _wrap(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("synthetic_data_only", True)
    payload.setdefault("no_medical_claims", True)
    if "degraded" not in payload:
        payload["degraded"] = bool(payload.get("degraded_components"))
    if "degraded_components" not in payload:
        payload["degraded_components"] = []
    if "limitations" not in payload:
        payload["limitations"] = []
    return payload


@router.get("/status")
def mission_status() -> dict[str, Any]:
    """Unified mission control status snapshot."""
    try:
        return _wrap(build_mission_status())
    except Exception as exc:  # noqa: BLE001 — optional offline must not 500
        return _wrap(
            {
                "phase": "phase_8",
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").UTC
                ).isoformat(),
                "system_mode": "degraded",
                "degraded": True,
                "degraded_components": ["mission_status_builder"],
                "limitations": [f"Mission status builder error: {exc}"],
                "components": {},
            }
        )


@router.get("/timeline")
def mission_timeline() -> dict[str, Any]:
    """Ordered mission timeline across the operational loop."""
    try:
        return _wrap(build_mission_timeline())
    except Exception as exc:  # noqa: BLE001
        return _wrap(
            {
                "phase": "phase_8",
                "events": [],
                "degraded": True,
                "degraded_components": ["mission_timeline_builder"],
                "limitations": [f"Mission timeline builder error: {exc}"],
            }
        )


@router.get("/evidence")
def mission_evidence() -> dict[str, Any]:
    """Unified internal Evidence Center index."""
    try:
        index = build_evidence_index(force_refresh=True)
        missing = [i["id"] for i in index["items"] if i["status"] == "missing"]
        not_generated = [i["id"] for i in index["items"] if i["status"] == "not_generated"]
        degraded = bool(missing)
        limitations: list[str] = ["Evidence index regenerated from disk"]
        if missing:
            limitations = [f"{len(missing)} committed evidence items missing on disk"]
        elif not_generated:
            limitations = [
                f"{len(not_generated)} optional/generated artifacts not yet produced locally"
            ]
        return _wrap(
            {
                **index,
                "degraded": degraded,
                "degraded_components": ["evidence_missing"] if missing else [],
                "limitations": limitations,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _wrap(
            {
                "phase": "phase_8",
                "items": [],
                "degraded": True,
                "degraded_components": ["evidence_index"],
                "limitations": [f"Evidence index error: {exc}"],
            }
        )


@router.get("/scenarios")
def mission_scenarios() -> dict[str, Any]:
    """Available Phase 8 scenario definitions."""
    payload = list_scenarios()
    return _wrap(
        {
            **payload,
            "degraded": False,
            "degraded_components": [],
            "limitations": ["Scenarios run offline without mandatory ROS2/FL/RL retraining"],
        }
    )


@router.post("/scenarios/run")
def mission_scenarios_run(body: ScenarioRunRequest) -> dict[str, Any]:
    """Run a lightweight deterministic Phase 8 scenario."""
    from apps.api.app.mission.constants import SCENARIO_NAMES

    if body.scenario not in SCENARIO_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{body.scenario}'. Valid: {list(SCENARIO_NAMES)}",
        )
    try:
        result = run_scenario(body.scenario, enrich_from_api=True)
        return _wrap(
            {
                **result,
                "degraded": False,
                "degraded_components": [],
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        return _wrap(
            {
                "scenario": body.scenario,
                "status": "error",
                "degraded": True,
                "degraded_components": ["scenario_runner"],
                "limitations": [f"Scenario runner error: {exc}"],
            }
        )
