"""In-memory telemetry counters and connection flags."""

from dataclasses import dataclass


@dataclass
class TelemetryState:
    """Runtime telemetry metrics (Phase 1 + Phase 2)."""

    received_events: int = 0
    valid_events: int = 0
    invalid_events: int = 0
    redis_writes: int = 0
    mqtt_connected: bool = False
    redis_connected: bool = False
    websocket_ready: bool = True
    last_error: str | None = None
    last_scenario: str | None = None
    # Phase 2 model score counters
    model_scores_received: int = 0
    model_scores_broadcast: int = 0
    model_score_stream_connected: bool = False
    last_model_score_at: str | None = None
    last_model_name: str | None = None


telemetry_state = TelemetryState()
