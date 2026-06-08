"""Lightweight JSON structured logging for Phase 7 operational events."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("axon.operational")


def log_event(
    *,
    level: str,
    service: str,
    event: str,
    message: str,
    status: str | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
    event_id: str | None = None,
    component: str | None = None,
    error_type: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit one structured JSON log line and return the payload."""
    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.upper(),
        "service": service,
        "event": event,
        "message": message,
    }
    if status is not None:
        payload["status"] = status
    if trace_id is not None:
        payload["trace_id"] = trace_id
    if run_id is not None:
        payload["run_id"] = run_id
    if event_id is not None:
        payload["event_id"] = event_id
    if component is not None:
        payload["component"] = component
    if error_type is not None:
        payload["error_type"] = error_type
    if extra:
        payload.update(extra)

    line = json.dumps(payload, separators=(",", ":"))
    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(line)
    return payload
