"""In-memory telemetry counters and connection flags."""

from dataclasses import dataclass


@dataclass
class TelemetryState:
    """Runtime telemetry metrics (Phase 1)."""

    received_events: int = 0
    valid_events: int = 0
    invalid_events: int = 0
    redis_writes: int = 0
    mqtt_connected: bool = False
    redis_connected: bool = False
    websocket_ready: bool = True
    last_error: str | None = None
    last_scenario: str | None = None


telemetry_state = TelemetryState()
