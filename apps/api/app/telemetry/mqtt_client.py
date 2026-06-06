"""Async MQTT subscriber with background reconnection."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

import aiomqtt

from apps.api.app.schemas.events import SensorEventV1
from apps.api.app.telemetry.redis_streams import append_sensor_event
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.telemetry.topic_router import (
    MQTT_SUBSCRIBE_TOPICS,
    ROBOT_STREAM,
    SENSOR_STREAMS,
    stream_for_topic,
)
from apps.api.app.telemetry.websocket_manager import ws_manager

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

MAX_CONNECT_ATTEMPTS = 10
CONNECT_BACKOFF_SECONDS = 2


def event_to_ws_message(event: SensorEventV1) -> dict:
    return {"type": "event", "event": event.model_dump(mode="json")}


def channel_for_signal(signal_type: str) -> str:
    return "robot-state" if signal_type == "robot_state" else "sensors"


async def handle_mqtt_message(topic: str, payload: bytes, redis: Redis | None) -> None:
    """Validate, persist, and broadcast one MQTT payload."""
    telemetry_state.received_events += 1
    try:
        raw = json.loads(payload.decode())
        event = SensorEventV1.model_validate(raw)
    except Exception as exc:
        telemetry_state.invalid_events += 1
        telemetry_state.last_error = f"validation_failed: {exc}"
        logger.warning("Invalid MQTT event on topic=%s error=%s", topic, exc)
        return

    stream = stream_for_topic(topic)
    if stream is None:
        telemetry_state.invalid_events += 1
        logger.warning("Unknown MQTT topic (no stream mapping): %s", topic)
        return

    telemetry_state.valid_events += 1
    scenario = event.metadata.get("scenario")
    if isinstance(scenario, str):
        telemetry_state.last_scenario = scenario

    if redis is not None:
        await append_sensor_event(redis, stream, event)

    message = event_to_ws_message(event)
    channel = channel_for_signal(event.signal_type)
    await ws_manager.broadcast(channel, message)
    await ws_manager.broadcast(
        "health",
        {"type": "status", "status": "ok", "component": "telemetry"},
    )


async def mqtt_subscriber_loop(host: str, port: int, redis: Redis | None) -> None:
    """Background MQTT consumer with retry/backoff; does not block API startup."""
    attempt = 0
    while True:
        try:
            attempt += 1
            logger.info(
                "MQTT connect attempt %s/%s to %s:%s",
                attempt,
                MAX_CONNECT_ATTEMPTS,
                host,
                port,
            )
            async with aiomqtt.Client(hostname=host, port=port) as client:
                telemetry_state.mqtt_connected = True
                attempt = 0
                for topic in MQTT_SUBSCRIBE_TOPICS:
                    await client.subscribe(topic)
                logger.info("MQTT subscribed topics=%s", MQTT_SUBSCRIBE_TOPICS)
                async for message in client.messages:
                    await handle_mqtt_message(str(message.topic), message.payload, redis)
        except asyncio.CancelledError:
            telemetry_state.mqtt_connected = False
            raise
        except Exception as exc:
            telemetry_state.mqtt_connected = False
            telemetry_state.last_error = f"mqtt_error: {exc}"
            logger.warning("MQTT connection failed (attempt %s): %s", attempt, exc)
            if attempt >= MAX_CONNECT_ATTEMPTS:
                logger.warning("Max MQTT attempts reached; continuing retry loop")
                attempt = 0
            await asyncio.sleep(CONNECT_BACKOFF_SECONDS)


async def get_initial_sensor_messages(redis: Redis | None) -> list[dict]:
    from apps.api.app.telemetry.redis_streams import get_last_events_by_signal

    return await get_last_events_by_signal(redis, SENSOR_STREAMS)


async def get_initial_robot_messages(redis: Redis | None) -> list[dict]:
    from apps.api.app.telemetry.redis_streams import get_last_events_by_signal

    return await get_last_events_by_signal(redis, [ROBOT_STREAM])
