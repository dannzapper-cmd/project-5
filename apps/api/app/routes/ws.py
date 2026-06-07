"""WebSocket routes for live telemetry."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from apps.api.app.telemetry.mqtt_client import (
    get_initial_robot_messages,
    get_initial_sensor_messages,
)
from apps.api.app.telemetry.redis_streams import get_last_model_scores_by_name
from apps.api.app.telemetry.websocket_manager import (
    AWAITING_MODEL_SCORES_MESSAGE,
    ws_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])


async def _hold_connection(channel: str, websocket: WebSocket) -> None:
    """Keep connection open until client disconnects."""
    try:
        while True:
            await asyncio.sleep(30)
            await ws_manager.send_json(
                websocket,
                {"type": "status", "status": "connected", "channel": channel},
            )
    except (WebSocketDisconnect, RuntimeError):
        pass


@router.websocket("/ws/v1/sensors")
async def ws_sensors(websocket: WebSocket) -> None:
    redis = websocket.app.state.redis
    await ws_manager.connect("sensors", websocket)
    try:
        initial = await get_initial_sensor_messages(redis)
        await ws_manager.send_initial_or_waiting(websocket, initial)
        await _hold_connection("sensors", websocket)
    finally:
        await ws_manager.disconnect("sensors", websocket)


@router.websocket("/ws/v1/robot-state")
async def ws_robot_state(websocket: WebSocket) -> None:
    redis = websocket.app.state.redis
    await ws_manager.connect("robot-state", websocket)
    try:
        initial = await get_initial_robot_messages(redis)
        await ws_manager.send_initial_or_waiting(websocket, initial)
        await _hold_connection("robot-state", websocket)
    finally:
        await ws_manager.disconnect("robot-state", websocket)


@router.websocket("/ws/v1/health")
async def ws_health(websocket: WebSocket) -> None:
    await ws_manager.connect("health", websocket)
    try:
        await ws_manager.send_json(
            websocket,
            {"type": "status", "status": "ok", "component": "ws-health"},
        )
        await _hold_connection("health", websocket)
    finally:
        await ws_manager.disconnect("health", websocket)


@router.websocket("/ws/v1/model-scores")
async def ws_model_scores(websocket: WebSocket) -> None:
    redis = websocket.app.state.redis
    await ws_manager.connect("model-scores", websocket)
    try:
        initial = await get_last_model_scores_by_name(redis, limit=10)
        if initial:
            for message in initial:
                await ws_manager.send_json(websocket, message)
        else:
            await ws_manager.send_json(websocket, AWAITING_MODEL_SCORES_MESSAGE)
        await _hold_connection("model-scores", websocket)
    finally:
        await ws_manager.disconnect("model-scores", websocket)


@router.websocket("/ws/v1/agents")
async def ws_agents(websocket: WebSocket) -> None:
    from apps.api.app.agents.service import get_recent_traces

    await ws_manager.connect("agents", websocket)
    try:
        for trace in get_recent_traces(20):
            await ws_manager.send_json(websocket, {"type": "agent_trace", "event": trace})
        await _hold_connection("agents", websocket)
    finally:
        await ws_manager.disconnect("agents", websocket)


@router.websocket("/ws/v1/decisions")
async def ws_decisions(websocket: WebSocket) -> None:
    from apps.api.app.agents.service import get_current_decision, get_decision_history

    await ws_manager.connect("decisions", websocket)
    try:
        current = get_current_decision()
        if current:
            await ws_manager.send_json(websocket, {"type": "decision", "event": current})
        for decision in get_decision_history(10):
            await ws_manager.send_json(websocket, {"type": "decision", "event": decision})
        await _hold_connection("decisions", websocket)
    finally:
        await ws_manager.disconnect("decisions", websocket)


@router.websocket("/ws/v1/safety")
async def ws_safety(websocket: WebSocket) -> None:
    from apps.api.app.agents.service import get_safety_status

    await ws_manager.connect("safety", websocket)
    try:
        await ws_manager.send_json(
            websocket, {"type": "safety_status", "status": get_safety_status()}
        )
        await _hold_connection("safety", websocket)
    finally:
        await ws_manager.disconnect("safety", websocket)


@router.websocket("/ws/v1/twin")
async def ws_twin(websocket: WebSocket) -> None:
    from apps.api.app.twin.service import build_twin_state, get_latest_twin_state

    redis = websocket.app.state.redis
    await ws_manager.connect("twin", websocket)
    try:
        latest = get_latest_twin_state()
        if latest is None:
            latest = await build_twin_state(redis)
        await ws_manager.send_json(
            websocket,
            {"type": "twin_state", "state": latest.model_dump(mode="json")},
        )
        await _hold_connection("twin", websocket)
    finally:
        await ws_manager.disconnect("twin", websocket)


@router.websocket("/ws/v1/nav-slam")
async def ws_nav_slam(websocket: WebSocket) -> None:
    from apps.api.app.nav_slam.service import get_nav_slam_state

    await ws_manager.connect("nav-slam", websocket)
    try:
        state = get_nav_slam_state()
        await ws_manager.send_json(
            websocket,
            {"type": "nav_slam_state", "state": state.model_dump(mode="json")},
        )
        await _hold_connection("nav-slam", websocket)
    finally:
        await ws_manager.disconnect("nav-slam", websocket)
