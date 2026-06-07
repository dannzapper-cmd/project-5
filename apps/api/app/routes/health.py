"""Health check route."""

from fastapi import APIRouter

from apps.api.app.core.config import settings
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.telemetry.websocket_manager import ws_manager
from apps.api.app.twin.service import get_latest_twin_state, get_twin_service_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str | int | bool | dict]:
    """Return service health and Phase 1 runtime metadata."""
    twin = get_latest_twin_state()
    twin_status = get_twin_service_status()
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
    }
