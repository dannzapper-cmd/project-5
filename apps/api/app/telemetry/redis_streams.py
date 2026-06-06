"""Redis Streams append and read helpers (async)."""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

from apps.api.app.schemas.events import SensorEventV1
from apps.api.app.telemetry.state import telemetry_state

logger = logging.getLogger(__name__)

# Phase 1 local-development retention policy (approximate MAXLEN per stream).
STREAM_MAXLEN = 1000


async def append_sensor_event(redis: Redis, stream: str, event: SensorEventV1) -> str | None:
    """Append validated sensor event to Redis stream with bounded retention."""
    payload = event.model_dump(mode="json")
    fields = {
        "event_id": event.event_id,
        "timestamp": payload["timestamp"],
        "trace_id": event.trace_id,
        "source": event.source,
        "signal_type": event.signal_type,
        "payload": json.dumps(payload),
    }
    try:
        entry_id = await redis.xadd(
            stream,
            fields,
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )
        telemetry_state.redis_writes += 1
        return entry_id
    except Exception as exc:
        telemetry_state.last_error = f"redis_write_failed: {exc}"
        logger.exception("Redis XADD failed for stream=%s", stream)
        return None


async def get_last_event(redis: Redis | None, stream: str) -> dict[str, Any] | None:
    """Fetch most recent event payload from a stream."""
    if redis is None:
        return None
    try:
        entries = await redis.xrevrange(stream, count=1)
        if not entries:
            return None
        _entry_id, fields = entries[0]
        raw = fields.get(b"payload") or fields.get("payload")
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        data = json.loads(raw)
        return {"type": "event", "event": data}
    except Exception as exc:
        logger.warning("Failed to read last event from %s: %s", stream, exc)
        return None


async def get_last_events_by_signal(
    redis: Redis | None,
    streams: list[str],
) -> list[dict[str, Any]]:
    """Fetch last event per stream for WebSocket initial state."""
    messages: list[dict[str, Any]] = []
    if redis is None:
        return messages
    for stream in streams:
        msg = await get_last_event(redis, stream)
        if msg:
            messages.append(msg)
    return messages
