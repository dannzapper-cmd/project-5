"""Health, readiness, and liveness routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from apps.api.app.core.config import settings
from apps.api.app.nav_slam.service import get_service_status as get_nav_slam_service_status
from apps.api.app.observability import events
from apps.api.app.observability.structured_log import log_event
from apps.api.app.reliability.service_status import build_readiness, build_service_status
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.telemetry.websocket_manager import ws_manager
from apps.api.app.twin.service import get_latest_twin_state, get_twin_service_status

router = APIRouter(tags=["health"])


def _trace_id(request: Request) -> str | None:
    return getattr(request.state, "trace_id", None)


@router.get("/health/live")
def health_live(request: Request) -> dict[str, str]:
    """Lightweight liveness probe — API process is alive."""
    trace_id = _trace_id(request)
    payload = {
        "status": "ok",
        "service": settings.service_name,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    log_event(
        level="debug",
        service=settings.service_name,
        event=events.HEALTH_CHECK_COMPLETED,
        message="Liveness check completed",
        status="ok",
        trace_id=trace_id,
        component="liveness",
    )
    return payload


@router.get("/health/ready")
def health_ready(request: Request) -> JSONResponse:
    """Readiness probe with required vs optional dependency breakdown."""
    trace_id = _trace_id(request)
    payload = build_readiness(trace_id=trace_id)
    status_code = 503 if payload["status"] == "error" else 200
    return JSONResponse(content=payload, status_code=status_code)


@router.get("/status/services")
def status_services(request: Request) -> dict:
    """Structured component status for operational diagnostics."""
    trace_id = _trace_id(request)
    return build_service_status(trace_id=trace_id)


@router.get("/health")
def health() -> dict[str, str | int | bool | dict]:
    """Return service health and Phase 1 runtime metadata (legacy aggregate)."""
    twin = get_latest_twin_state()
    twin_status = get_twin_service_status()
    nav_slam_status = get_nav_slam_service_status()
    ros2_status = "offline"
    if twin is not None:
        ros2_status = twin.ros2_bridge.status

    return {
        "status": "ok",
        "service": settings.service_name,
        "phase": settings.phase,
        "version": settings.version,
        "mqtt_configured": bool(settings.mqtt_host),
        "redis_configured": bool(settings.redis_url),
        "websocket_ready": telemetry_state.websocket_ready,
        "mqtt_connected": telemetry_state.mqtt_connected,
        "redis_connected": telemetry_state.redis_connected,
        "websocket_clients": ws_manager.client_count(),
        "twin_service": {
            "running": twin_status["running"],
            "broadcast_hz": twin_status["broadcast_hz"],
            "last_broadcast": twin_status["last_broadcast"],
        },
        "ros2_bridge": {
            "status": ros2_status,
            "last_topic_publish": (
                twin.ros2_bridge.last_topic_publish.isoformat()
                if twin and twin.ros2_bridge.last_topic_publish
                else None
            ),
        },
        "nav_slam_minilab": {
            "bridge_status": nav_slam_status["bridge_status"],
            "nav_status": nav_slam_status["nav_status"],
            "slam_status": nav_slam_status["slam_status"],
            "last_ingest_at": nav_slam_status["last_ingest_at"],
        },
    }
