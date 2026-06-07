"""Phase 5.5 ROS2 Nav2 + SLAM MiniLab REST routes.

Integration path for the MiniLab (services/ros2-nav-slam-minilab):
  - GET  /api/v1/nav-slam/status         dashboard status (graceful offline)
  - POST /api/v1/nav-slam/goal           operator sends a navigation goal
  - POST /api/v1/nav-slam/command        operator command (start_mapping/reset/send_goal)
  - POST /api/v1/nav-slam/ingest         ROS2 bridge pushes live MiniLab state
  - GET  /api/v1/nav-slam/pending-command  ROS2 bridge polls operator commands
  - GET  /api/v1/nav-slam/service-status   runtime metadata

State is mirrored via apps.api.app.nav_slam.service and broadcast on the shared
WebSocket channel "nav-slam" (/ws/v1/nav-slam), mirroring the Phase 5 twin path.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.app.nav_slam.service import (
    get_nav_slam_state,
    get_nav_slam_status_dict,
    get_pending_command,
    get_service_status,
    handle_command,
    submit_goal,
    update_from_ingest,
)
from apps.api.app.schemas.nav_slam import (
    NavGoalV1,
    NavSlamCommandRequestV1,
    NavSlamCommandResponseV1,
    NavSlamIngestV1,
    NavSlamStateV1,
)
from apps.api.app.telemetry.websocket_manager import ws_manager

router = APIRouter(prefix="/api/v1/nav-slam", tags=["nav-slam"])


@router.get("/status")
def nav_slam_status() -> dict:
    """Latest MiniLab navigation/mapping status (offline when bridge inactive)."""
    return get_nav_slam_status_dict()


@router.get("/state", response_model=NavSlamStateV1)
def nav_slam_state() -> NavSlamStateV1:
    """Versioned MiniLab state snapshot."""
    return get_nav_slam_state()


@router.post("/goal", response_model=NavSlamCommandResponseV1)
def post_goal(goal: NavGoalV1) -> NavSlamCommandResponseV1:
    """Queue a navigation goal for the MiniLab (picked up by the ROS2 bridge)."""
    return submit_goal(goal, requested_by="api-operator")


@router.post("/command", response_model=NavSlamCommandResponseV1)
def post_command(body: NavSlamCommandRequestV1) -> NavSlamCommandResponseV1:
    """Queue a MiniLab command (start_mapping / send_goal / reset)."""
    if not body.requested_by.strip():
        raise HTTPException(status_code=422, detail="requested_by must not be empty")
    return handle_command(body)


@router.post("/ingest", response_model=NavSlamStateV1)
async def post_ingest(body: NavSlamIngestV1) -> NavSlamStateV1:
    """ROS2 bridge pushes live MiniLab state; broadcast to dashboard WebSocket."""
    state = update_from_ingest(body)
    await ws_manager.broadcast(
        "nav-slam",
        {"type": "nav_slam_state", "state": state.model_dump(mode="json")},
    )
    return state


@router.get("/pending-command")
def pending_command(after_seq: int = 0) -> dict:
    """ROS2 bridge polls for operator commands newer than after_seq."""
    cmd = get_pending_command(after_seq)
    if cmd is None:
        return {"command": None, "seq": after_seq}
    return cmd


@router.get("/service-status")
def service_status() -> dict:
    """MiniLab bridge runtime metadata."""
    return get_service_status()
