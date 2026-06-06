"""Health check route."""

from fastapi import APIRouter

from apps.api.app.core.config import settings
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.telemetry.websocket_manager import ws_manager

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str | int | bool]:
    """Return service health and Phase 1 runtime metadata."""
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
    }
