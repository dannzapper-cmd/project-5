"""Phase 5 Digital Twin REST routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from apps.api.app.schemas.twin import (
    DigitalTwinStateV1,
    TwinCommandRequestV1,
    TwinCommandResponseV1,
)
from apps.api.app.twin.service import (
    build_twin_state,
    get_latest_twin_state,
    get_twin_service_status,
    handle_twin_command,
    record_ros2_heartbeat,
)

router = APIRouter(prefix="/api/v1/twin", tags=["twin"])


@router.get("/state", response_model=DigitalTwinStateV1)
async def get_twin_state(request: Request) -> DigitalTwinStateV1:
    """Return latest digital twin snapshot (cached or freshly built)."""
    latest = get_latest_twin_state()
    if latest is not None:
        return latest
    redis = request.app.state.redis
    return await build_twin_state(redis)


@router.post("/command", response_model=TwinCommandResponseV1)
async def post_twin_command(body: TwinCommandRequestV1) -> TwinCommandResponseV1:
    """Execute a safe robot/twin command with validation and trace linkage."""
    if not body.requested_by.strip():
        raise HTTPException(status_code=422, detail="requested_by must not be empty")
    return await handle_twin_command(body)


@router.get("/status")
def twin_status() -> dict:
    """Twin service runtime metadata."""
    return get_twin_service_status()


@router.post("/ros2-heartbeat")
def ros2_heartbeat(command_status: str | None = None) -> dict[str, str]:
    """ROS2 bridge liveness and last command status."""
    record_ros2_heartbeat(command_status)
    return {"status": "ok"}
