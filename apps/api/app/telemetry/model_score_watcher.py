"""Background task: tail model_scores stream and broadcast to WebSocket."""

from __future__ import annotations

import asyncio
import json
import logging

from redis.asyncio import Redis

from apps.api.app.schemas.events import ModelScoreEventV1
from apps.api.app.telemetry.model_score_streams import MODEL_SCORE_STREAM
from apps.api.app.telemetry.redis_streams import model_score_to_ws_message
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.telemetry.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


async def watch_model_scores(websocket_manager: WebSocketManager, redis: Redis | None) -> None:
    """Tail axon:v1:stream:model_scores and broadcast ModelScoreEventV1."""
    if redis is None:
        telemetry_state.model_score_stream_connected = False
        return

    telemetry_state.model_score_stream_connected = True
    last_id = "$"

    while True:
        try:
            events = await redis.xread(
                streams={MODEL_SCORE_STREAM: last_id},
                block=1000,
                count=10,
            )
            if events:
                for _stream, messages in events:
                    for msg_id, data in messages:
                        last_id = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                        raw = data.get(b"payload") or data.get("payload")
                        if raw is None:
                            continue
                        if isinstance(raw, bytes):
                            raw = raw.decode()
                        payload = json.loads(raw)
                        event = ModelScoreEventV1.model_validate(payload)
                        telemetry_state.model_scores_received += 1
                        telemetry_state.last_model_score_at = event.timestamp.isoformat()
                        telemetry_state.last_model_name = event.model_name
                        message = model_score_to_ws_message(event)
                        await websocket_manager.broadcast("model-scores", message)
                        telemetry_state.model_scores_broadcast += 1
        except asyncio.CancelledError:
            telemetry_state.model_score_stream_connected = False
            raise
        except Exception as exc:
            logger.error("model_score_watcher error: %s", exc)
            telemetry_state.last_error = f"model_score_watcher: {exc}"
            await asyncio.sleep(2)
