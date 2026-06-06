"""Telemetry status route."""

from fastapi import APIRouter

from apps.api.app.core.config import settings
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.telemetry.topic_router import MQTT_SUBSCRIBE_TOPICS, TOPIC_TO_STREAM
from apps.api.app.telemetry.websocket_manager import ws_manager

router = APIRouter(tags=["telemetry"])


@router.get("/telemetry/status")
def telemetry_status() -> dict:
    """Return Phase 1 telemetry spine counters and configuration."""
    return {
        "phase": "Phase 1 - Telemetry Spine",
        "service": settings.service_name,
        "version": settings.version,
        "counters": {
            "received_events": telemetry_state.received_events,
            "valid_events": telemetry_state.valid_events,
            "invalid_events": telemetry_state.invalid_events,
            "redis_writes": telemetry_state.redis_writes,
            "websocket_clients": ws_manager.client_count(),
            "websocket_sensors_clients": ws_manager.channel_count("sensors"),
            "websocket_robot_state_clients": ws_manager.channel_count("robot-state"),
        },
        "connectivity": {
            "mqtt_connected": telemetry_state.mqtt_connected,
            "redis_connected": telemetry_state.redis_connected,
            "websocket_ready": telemetry_state.websocket_ready,
        },
        "configured_topics": MQTT_SUBSCRIBE_TOPICS,
        "redis_stream_mapping": TOPIC_TO_STREAM,
        "last_scenario": telemetry_state.last_scenario,
        "last_error": telemetry_state.last_error,
    }
