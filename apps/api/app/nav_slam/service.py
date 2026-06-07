# AXON Phase 5.5 Nav2 + SLAM MiniLab backend integration
#
# This module mirrors the live MiniLab navigation/mapping state pushed by the
# ROS2 bridge (services/ros2-nav-slam-minilab) and exposes operator commands
# that the bridge polls and forwards into ROS2 services.
#
# Integration with Phase 5 conventions:
#   - Versioned schemas in apps/api/app/schemas/nav_slam.py (same module family
#     as DigitalTwinStateV1 in apps/api/app/schemas/twin.py)
#   - WebSocket broadcast via the shared ws_manager on channel "nav-slam"
#     (mirrors the Phase 5 "twin" channel / /ws/v1/twin)
#   - Heartbeat/offline detection mirrors twin.service._ros2_status()
#
# The MiniLab is a simulated robotics lab. No physical robot, no clinical
# autonomy, no medical claims, no patient data.

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from apps.api.app.schemas.nav_slam import (
    NavGoalV1,
    NavSlamCommandRequestV1,
    NavSlamCommandResponseV1,
    NavSlamCommandStatus,
    NavSlamIngestV1,
    NavSlamStateV1,
    SlamMapStatusV1,
)

logger = logging.getLogger(__name__)

# Bridge is considered offline if no ingest/heartbeat received within this window.
BRIDGE_OFFLINE_TTL_SECONDS = 15

_state: NavSlamStateV1 = NavSlamStateV1()
_last_ingest_at: datetime | None = None
_pending_command: dict[str, Any] | None = None
_command_seq: int = 0


def reset_state() -> None:
    """Reset MiniLab mirror state (used by tests and the reset command)."""
    global _state, _last_ingest_at, _pending_command, _command_seq
    _state = NavSlamStateV1()
    _last_ingest_at = None
    _pending_command = None
    _command_seq = 0


def _bridge_status(now: datetime) -> str:
    if _last_ingest_at is None:
        return "offline"
    age = (now - _last_ingest_at).total_seconds()
    if age > BRIDGE_OFFLINE_TTL_SECONDS:
        return "offline"
    if _state.slam.status == "degraded" or _state.nav_status in ("blocked", "failed"):
        return "degraded"
    return "online"


def get_nav_slam_state() -> NavSlamStateV1:
    """Return the latest mirrored MiniLab state with live bridge status."""
    now = datetime.now(UTC)
    status = _bridge_status(now)
    # Return a copy with the freshly computed bridge status so offline is honest.
    return _state.model_copy(update={"bridge_status": status})


def get_nav_slam_status_dict() -> dict[str, Any]:
    """Dashboard-friendly status payload (graceful offline state)."""
    state = get_nav_slam_state()
    payload = state.model_dump(mode="json")
    payload["bridge_offline_ttl_seconds"] = BRIDGE_OFFLINE_TTL_SECONDS
    payload["safety_notice"] = (
        "Simulated robotics navigation/mapping lab. No physical robot. "
        "No clinical autonomy. No medical claims. No patient data."
    )
    return payload


def update_from_ingest(ingest: NavSlamIngestV1) -> NavSlamStateV1:
    """Apply a partial state update pushed by the ROS2 bridge."""
    global _state, _last_ingest_at
    now = datetime.now(UTC)
    _last_ingest_at = now

    updates: dict[str, Any] = {
        "timestamp": now,
        "last_heartbeat": now,
        "bridge_status": "online",
    }
    if ingest.nav_status is not None:
        updates["nav_status"] = ingest.nav_status
    updates["nav_status_reason"] = ingest.nav_status_reason
    if ingest.active_demo is not None:
        updates["active_demo"] = ingest.active_demo
    if ingest.robot_pose is not None:
        updates["robot_pose"] = ingest.robot_pose
    if ingest.goal is not None:
        updates["goal"] = ingest.goal
    if ingest.path is not None:
        updates["path"] = ingest.path
    if ingest.slam is not None:
        updates["slam"] = ingest.slam
    if ingest.trace_id is not None:
        updates["trace_id"] = ingest.trace_id

    _state = _state.model_copy(update=updates)
    return _state


def handle_command(request: NavSlamCommandRequestV1) -> NavSlamCommandResponseV1:
    """Validate a MiniLab command and enqueue it for the ROS2 bridge to pick up."""
    global _pending_command, _command_seq, _state

    trace_id = f"navcmd-{uuid4().hex[:12]}"
    status: NavSlamCommandStatus = "accepted"
    reason: str | None = None

    if request.command == "send_goal":
        if request.goal is None:
            status = "rejected"
            reason = "send_goal requires a goal (x, y, theta_deg)."
        else:
            reason = f"Goal queued for MiniLab at ({request.goal.x:.2f}, {request.goal.y:.2f})."
    elif request.command == "start_mapping":
        reason = "Mapping start queued for SLAM Toolbox."
    elif request.command == "reset":
        reason = "MiniLab reset queued."
    else:  # pragma: no cover - guarded by schema Literal
        status = "rejected"
        reason = f"Unknown command: {request.command}"

    if status == "accepted":
        _command_seq += 1
        _pending_command = {
            "seq": _command_seq,
            "command": request.command,
            "requested_by": request.requested_by,
            "demo": request.demo,
            "goal": request.goal.model_dump(mode="json") if request.goal else None,
            "reason": reason,
            "trace_id": trace_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return NavSlamCommandResponseV1(
        status=status,
        command=request.command,
        reason=reason,
        trace_id=trace_id,
    )


def submit_goal(goal: NavGoalV1, requested_by: str) -> NavSlamCommandResponseV1:
    """Convenience wrapper used by the REST goal endpoint."""
    return handle_command(
        NavSlamCommandRequestV1(
            command="send_goal", requested_by=requested_by, goal=goal
        )
    )


def get_pending_command(after_seq: int = 0) -> dict[str, Any] | None:
    """Return the queued command for the ROS2 bridge, if newer than after_seq."""
    if _pending_command is None:
        return None
    if _pending_command["seq"] <= after_seq:
        return None
    return dict(_pending_command)


def get_service_status() -> dict[str, Any]:
    """Runtime metadata for /api/v1/nav-slam/service-status and health."""
    now = datetime.now(UTC)
    return {
        "bridge_status": _bridge_status(now),
        "last_ingest_at": _last_ingest_at.isoformat() if _last_ingest_at else None,
        "bridge_offline_ttl_seconds": BRIDGE_OFFLINE_TTL_SECONDS,
        "nav_status": _state.nav_status,
        "slam_status": _state.slam.status,
        "pending_command_seq": _pending_command["seq"] if _pending_command else 0,
    }


def empty_slam_status() -> SlamMapStatusV1:
    return SlamMapStatusV1()
