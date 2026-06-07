"""Phase 3 agent REST routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from apps.api.app.agents import failure_injection
from apps.api.app.agents.hitl import (
    append_decision_stream,
    get_current_pending,
    get_pending_decision,
    remove_pending_decision,
)
from apps.api.app.agents.service import (
    get_current_decision,
    get_decision_history,
    get_recent_traces,
    get_safety_status,
)
from apps.api.app.schemas.events import HumanResponseV1
from apps.api.app.telemetry.websocket_manager import ws_manager

router = APIRouter(prefix="/api/v1", tags=["agents"])


class HumanConfirmBody(BaseModel):
    operator_id: str = "operator-001"
    note: str = ""


@router.get("/agents/traces")
async def list_agent_traces(limit: int = 50) -> dict:
    """Return recent agent trace events."""
    return {"traces": get_recent_traces(limit), "count": len(get_recent_traces(limit))}


@router.get("/decisions/current")
async def current_decision(request: Request) -> dict:
    """Return current pending decision or none."""
    redis = request.app.state.redis
    pending = await get_current_pending(redis)
    if pending:
        return pending.model_dump(mode="json")
    current = get_current_decision()
    if current:
        return current
    return {"decision_id": None, "status": "none"}


@router.get("/decisions/history")
async def decision_history(limit: int = 50) -> dict:
    """Return recent decision events."""
    history = get_decision_history(limit)
    return {"decisions": history, "count": len(history)}


@router.post("/decisions/{decision_id}/confirm")
async def confirm_decision(decision_id: str, request: Request, body: HumanConfirmBody) -> dict:
    """Confirm a pending human-in-the-loop decision."""
    redis = request.app.state.redis
    decision = await get_pending_decision(redis, decision_id)
    if decision is None or decision.status != "pending_human_confirmation":
        raise HTTPException(status_code=404, detail="Pending decision not found")

    decision.status = "confirmed"
    decision.human_response = HumanResponseV1(
        operator_id=body.operator_id,
        response="confirmed",
        note=body.note,
        timestamp=datetime.now(UTC),
    )
    await append_decision_stream(redis, decision)
    await remove_pending_decision(redis, decision_id)
    payload = decision.model_dump(mode="json")
    await ws_manager.broadcast("decisions", {"type": "decision", "event": payload})
    return payload


@router.post("/decisions/{decision_id}/reject")
async def reject_decision(decision_id: str, request: Request, body: HumanConfirmBody) -> dict:
    """Reject a pending human-in-the-loop decision."""
    redis = request.app.state.redis
    decision = await get_pending_decision(redis, decision_id)
    if decision is None or decision.status != "pending_human_confirmation":
        raise HTTPException(status_code=404, detail="Pending decision not found")

    decision.status = "rejected"
    decision.human_response = HumanResponseV1(
        operator_id=body.operator_id,
        response="rejected",
        note=body.note,
        timestamp=datetime.now(UTC),
    )
    await append_decision_stream(redis, decision)
    await remove_pending_decision(redis, decision_id)
    payload = decision.model_dump(mode="json")
    await ws_manager.broadcast("decisions", {"type": "decision", "event": payload})
    return payload


@router.get("/safety/status")
async def safety_status() -> dict:
    """Return current safety panel status."""
    return get_safety_status()


@router.post("/failure-injection/{scenario}")
async def trigger_failure_injection(scenario: str) -> dict:
    """Activate a controlled failure injection scenario."""
    try:
        failure_injection.activate_injection(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "scenario": scenario,
        "status": "active",
        "active": failure_injection.active_scenarios(),
        "auto_reset_seconds": failure_injection.AUTO_RESET_SECONDS,
    }


@router.post("/failure-injection/reset")
async def reset_failure_injection() -> dict:
    """Clear all active failure injections."""
    failure_injection.reset_injections()
    return {"status": "reset", "active": []}
