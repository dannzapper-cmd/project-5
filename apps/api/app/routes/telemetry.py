"""Telemetry status route."""

from fastapi import APIRouter

from apps.api.app.core.config import settings
from apps.api.app.telemetry.model_score_streams import MODEL_SCORE_STREAM
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.telemetry.topic_router import MQTT_SUBSCRIBE_TOPICS, TOPIC_TO_STREAM
from apps.api.app.telemetry.websocket_manager import ws_manager

router = APIRouter(tags=["telemetry"])


@router.get("/telemetry/status")
def telemetry_status() -> dict:
    """Return Phase 2 telemetry + edge AI counters and configuration."""
    return {
        "phase": "Phase 3 - Agents + Safety",
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
            "websocket_model_scores_clients": ws_manager.channel_count("model-scores"),
            "model_scores_received": telemetry_state.model_scores_received,
            "model_scores_broadcast": telemetry_state.model_scores_broadcast,
        },
        "connectivity": {
            "mqtt_connected": telemetry_state.mqtt_connected,
            "redis_connected": telemetry_state.redis_connected,
            "websocket_ready": telemetry_state.websocket_ready,
            "model_score_stream_connected": telemetry_state.model_score_stream_connected,
        },
        "model_scores": {
            "stream": MODEL_SCORE_STREAM,
            "last_model_score_at": telemetry_state.last_model_score_at,
            "last_model_name": telemetry_state.last_model_name,
        },
        "configured_topics": MQTT_SUBSCRIBE_TOPICS,
        "redis_stream_mapping": TOPIC_TO_STREAM,
        "last_scenario": telemetry_state.last_scenario,
        "last_error": telemetry_state.last_error,
    }


@router.get("/model-scores/status")
def model_scores_status() -> dict:
    """Return model score stream status."""
    return {
        "stream": MODEL_SCORE_STREAM,
        "model_scores_received": telemetry_state.model_scores_received,
        "model_scores_broadcast": telemetry_state.model_scores_broadcast,
        "model_score_stream_connected": telemetry_state.model_score_stream_connected,
        "last_model_score_at": telemetry_state.last_model_score_at,
        "last_model_name": telemetry_state.last_model_name,
    }
