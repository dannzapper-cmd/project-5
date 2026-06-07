"""Redis-based durable human-in-the-loop decision storage."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from apps.api.app.agents.streams import (
    DECISION_STREAM,
    PENDING_DECISION_PREFIX,
    PENDING_DECISIONS_KEY,
)
from apps.api.app.schemas.events import DecisionEventV1

logger = logging.getLogger(__name__)

# Optional in-process cache keyed by decision_id
_pending_decisions: dict[str, DecisionEventV1] = {}


def cache_pending(decision: DecisionEventV1) -> None:
    """Update in-process cache."""
    _pending_decisions[decision.decision_id] = decision


def remove_from_cache(decision_id: str) -> None:
    """Remove from in-process cache."""
    _pending_decisions.pop(decision_id, None)


def get_cached_pending() -> dict[str, DecisionEventV1]:
    """Return in-process pending cache."""
    return _pending_decisions


async def store_pending_decision(redis: Redis | None, decision: DecisionEventV1) -> None:
    """Persist pending decision to Redis (source of truth) and cache."""
    cache_pending(decision)
    if redis is None:
        return
    try:
        payload = decision.model_dump(mode="json")
        key = f"{PENDING_DECISION_PREFIX}{decision.decision_id}"
        await redis.set(key, json.dumps(payload))
        await redis.sadd(PENDING_DECISIONS_KEY, decision.decision_id)
    except Exception as exc:
        logger.warning("Failed to store pending decision in Redis: %s", exc)


async def load_pending_decisions(redis: Redis | None) -> None:
    """Reload pending decisions from Redis on startup."""
    if redis is None:
        return
    try:
        decision_ids = await redis.smembers(PENDING_DECISIONS_KEY)
        for raw_id in decision_ids:
            decision_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
            key = f"{PENDING_DECISION_PREFIX}{decision_id}"
            raw = await redis.get(key)
            if raw is None:
                await redis.srem(PENDING_DECISIONS_KEY, decision_id)
                continue
            data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
            decision = DecisionEventV1.model_validate(data)
            if decision.status == "pending_human_confirmation":
                cache_pending(decision)
    except Exception as exc:
        logger.warning("Failed to load pending decisions: %s", exc)


async def get_pending_decision(
    redis: Redis | None, decision_id: str
) -> DecisionEventV1 | None:
    """Fetch pending decision from cache or Redis."""
    if decision_id in _pending_decisions:
        return _pending_decisions[decision_id]
    if redis is None:
        return None
    try:
        key = f"{PENDING_DECISION_PREFIX}{decision_id}"
        raw = await redis.get(key)
        if raw is None:
            return None
        data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        decision = DecisionEventV1.model_validate(data)
        cache_pending(decision)
        return decision
    except Exception as exc:
        logger.warning("Failed to get pending decision %s: %s", decision_id, exc)
        return None


async def get_current_pending(redis: Redis | None) -> DecisionEventV1 | None:
    """Return oldest pending decision or None."""
    if _pending_decisions:
        return min(_pending_decisions.values(), key=lambda d: d.timestamp)
    if redis is None:
        return None
    try:
        decision_ids = await redis.smembers(PENDING_DECISIONS_KEY)
        oldest: DecisionEventV1 | None = None
        for raw_id in decision_ids:
            decision_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
            decision = await get_pending_decision(redis, decision_id)
            if decision and decision.status == "pending_human_confirmation":
                if oldest is None or decision.timestamp < oldest.timestamp:
                    oldest = decision
        return oldest
    except Exception as exc:
        logger.warning("Failed to get current pending: %s", exc)
        return None


async def remove_pending_decision(redis: Redis | None, decision_id: str) -> None:
    """Remove pending decision from Redis and cache."""
    remove_from_cache(decision_id)
    if redis is None:
        return
    try:
        await redis.delete(f"{PENDING_DECISION_PREFIX}{decision_id}")
        await redis.srem(PENDING_DECISIONS_KEY, decision_id)
    except Exception as exc:
        logger.warning("Failed to remove pending decision: %s", exc)


async def append_decision_stream(redis: Redis | None, decision: DecisionEventV1) -> None:
    """Write decision event to Redis stream."""
    if redis is None:
        return
    try:
        payload = decision.model_dump(mode="json")
        await redis.xadd(
            DECISION_STREAM,
            {
                "event_id": decision.event_id,
                "decision_id": decision.decision_id,
                "timestamp": payload["timestamp"],
                "trace_id": decision.trace_id,
                "payload": json.dumps(payload),
            },
            maxlen=1000,
            approximate=True,
        )
    except Exception as exc:
        logger.warning("Failed to append decision stream: %s", exc)


async def expire_pending_decisions(
    redis: Redis | None,
    expiry_seconds: int,
    broadcast_fn: Any | None = None,
) -> list[DecisionEventV1]:
    """Mark expired pending decisions and write to stream."""
    expired: list[DecisionEventV1] = []
    now = datetime.now(UTC)
    to_check = list(_pending_decisions.values())
    for decision in to_check:
        age = (now - decision.timestamp).total_seconds()
        if age >= expiry_seconds and decision.status == "pending_human_confirmation":
            decision.status = "expired"  # type: ignore[assignment]
            expired.append(decision)
            await append_decision_stream(redis, decision)
            await remove_pending_decision(redis, decision.decision_id)
            if broadcast_fn:
                await broadcast_fn(decision)
    return expired


async def run_expiry_check(redis: Redis | None = None, expiry_seconds: int | None = None) -> None:
    """Run pending decision expiry (for tests and agent loop)."""
    ttl = expiry_seconds or int(os.getenv("AXON_HITL_EXPIRY_SECONDS", "120"))
    await expire_pending_decisions(redis, ttl)
