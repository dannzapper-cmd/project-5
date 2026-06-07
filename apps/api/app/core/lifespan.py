"""FastAPI lifespan: Redis + background tasks + Phase 3 agent loop + Phase 4 drift."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from apps.api.app.agents.service import agent_loop
from apps.api.app.core.config import settings
from apps.api.app.mlops.drift_watcher import drift_detector_loop
from apps.api.app.telemetry.model_score_watcher import watch_model_scores
from apps.api.app.telemetry.mqtt_client import mqtt_subscriber_loop
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.telemetry.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start Redis client and background tasks; cleanup on shutdown."""
    redis: Redis | None = None
    mqtt_task: asyncio.Task | None = None
    model_score_task: asyncio.Task | None = None
    agent_task: asyncio.Task | None = None
    drift_task: asyncio.Task | None = None

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

    model_score_task = asyncio.create_task(watch_model_scores(ws_manager, redis))
    logger.info("Model score watcher task started")

    agent_task = asyncio.create_task(agent_loop(redis, ws_manager))
    logger.info(
        "Phase 3 agent loop task started (interval=%ss)",
        settings.axon_agent_loop_interval_seconds,
    )

    drift_task = asyncio.create_task(drift_detector_loop(redis))
    logger.info("Drift detector task started")

    yield

    for task in (mqtt_task, model_score_task, agent_task, drift_task):
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    if redis is not None:
        await redis.aclose()
        telemetry_state.redis_connected = False
