"""WebSocket connection manager and broadcast helpers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

AWAITING_DATA_MESSAGE: dict[str, Any] = {
    "type": "status",
    "status": "awaiting_data",
    "message": "Waiting for synthetic telemetry...",
}

AWAITING_MODEL_SCORES_MESSAGE: dict[str, Any] = {
    "type": "waiting",
    "message": "Awaiting model scores...",
}


class WebSocketManager:
    """Manage WebSocket clients per channel."""

    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = {
            "sensors": set(),
            "robot-state": set(),
            "health": set(),
            "model-scores": set(),
            "agents": set(),
            "decisions": set(),
            "safety": set(),
            "twin": set(),
            "nav-slam": set(),
        }
        self._lock = asyncio.Lock()

    def client_count(self) -> int:
        return sum(len(clients) for clients in self._channels.values())

    def channel_count(self, channel: str) -> int:
        return len(self._channels.get(channel, set()))

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._channels.setdefault(channel, set()).add(websocket)

    async def disconnect(self, channel: str, websocket: WebSocket) -> None:
        async with self._lock:
            clients = self._channels.get(channel)
            if clients and websocket in clients:
                clients.remove(websocket)

    async def send_json(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        await websocket.send_text(json.dumps(message, default=str))

    async def send_initial_or_waiting(
        self,
        websocket: WebSocket,
        initial_messages: list[dict[str, Any]],
    ) -> None:
        if initial_messages:
            for message in initial_messages:
                await self.send_json(websocket, message)
        else:
            await self.send_json(websocket, AWAITING_DATA_MESSAGE)

    async def broadcast(self, channel: str, message: dict[str, Any]) -> None:
        async with self._lock:
            clients = list(self._channels.get(channel, set()))
        if not clients:
            return
        dead: list[WebSocket] = []
        text = json.dumps(message, default=str)
        for ws in clients:
            try:
                await ws.send_text(text)
            except (WebSocketDisconnect, RuntimeError):
                dead.append(ws)
            except Exception as exc:
                logger.warning("WebSocket send failed: %s", exc)
                dead.append(ws)
        for ws in dead:
            await self.disconnect(channel, ws)


ws_manager = WebSocketManager()
