"""FastAPI lifespan: Redis + background MQTT subscriber."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from apps.api.app.core.config import settings
from apps.api.app.telemetry.mqtt_client import mqtt_subscriber_loop
from apps.api.app.telemetry.state import telemetry_state

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start Redis client and MQTT background task; cleanup on shutdown."""
    redis: Redis | None = None
    mqtt_task: asyncio.Task | None = None

    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=False)
        await redis.ping()
        telemetry_state.redis_connected = True
        logger.info("Redis connected: %s", settings.redis_url)
    except Exception as exc:
        telemetry_state.redis_connected = False
        telemetry_state.last_error = f"redis_connect_failed: {exc}"
        logger.warning("Redis unavailable at startup: %s", exc)
        redis = None

    app.state.redis = redis

    mqtt_task = asyncio.create_task(
        mqtt_subscriber_loop(settings.mqtt_host, settings.mqtt_port, redis)
    )
    logger.info("MQTT background subscriber task started")

    yield

    if mqtt_task is not None:
        mqtt_task.cancel()
        try:
            await mqtt_task
        except asyncio.CancelledError:
            pass

    if redis is not None:
        await redis.aclose()
        telemetry_state.redis_connected = False
