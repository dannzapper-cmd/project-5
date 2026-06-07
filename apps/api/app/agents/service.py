"""Agent orchestration service: loop, graph execution, stream writes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from redis.asyncio import Redis

from apps.api.app.agents.failure_injection import (
    active_scenarios,
    evict_expired_injections,
    is_active,
)
from apps.api.app.agents.graph import get_compiled_graph
from apps.api.app.agents.hitl import (
    append_decision_stream,
    expire_pending_decisions,
    load_pending_decisions,
    store_pending_decision,
)
from apps.api.app.agents.state import AXONAgentState
from apps.api.app.agents.streams import AGENT_TRACE_STREAM, ALERT_STREAM
from apps.api.app.core.config import settings
from apps.api.app.langchain.rag import load_rag_documents
from apps.api.app.schemas.events import DecisionEventV1
from apps.api.app.telemetry.model_score_streams import MODEL_SCORE_STREAM
from apps.api.app.telemetry.topic_router import SENSOR_STREAMS

logger = logging.getLogger(__name__)

_graph_running: bool = False
LOOP_INTERVAL = int(os.getenv("AXON_AGENT_LOOP_INTERVAL_SECONDS", "5"))

_compiled_graph = None
_safety_status: dict[str, Any] = {
    "safety_mode": "deterministic",
    "stale_telemetry": False,
    "missing_signals": [],
    "low_confidence": False,
    "high_risk": False,
    "llm_authority": "advisory_only",
    "active_injections": [],
}
_recent_traces: list[dict] = []
_decision_history: list[dict] = []
_current_decision: dict | None = None


def get_compiled_graph_cached():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = get_compiled_graph()
    return _compiled_graph


def get_safety_status() -> dict[str, Any]:
    return dict(_safety_status)


def get_recent_traces(limit: int = 50) -> list[dict]:
    return _recent_traces[-limit:]


def get_decision_history(limit: int = 50) -> list[dict]:
    return _decision_history[-limit:]


def get_current_decision() -> dict | None:
    return _current_decision


async def _read_stream_snapshot(redis: Redis | None, streams: list[str]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    if redis is None:
        return snapshot
    for stream in streams:
        try:
            entries = await redis.xrevrange(stream, count=1)
            if not entries:
                continue
            _eid, fields = entries[0]
            raw = fields.get(b"payload") or fields.get("payload")
            if raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode()
            data = json.loads(raw)
            signal = data.get("signal_type") or stream.split(":")[-1]
            snapshot[signal] = {
                "timestamp": data.get("timestamp"),
                "quality": data.get("quality"),
                "values": data.get("values"),
                "event_id": data.get("event_id"),
            }
        except Exception as exc:
            logger.debug("Stream read failed for %s: %s", stream, exc)
    return snapshot


async def _read_model_scores(redis: Redis | None) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    if redis is None:
        return snapshot
    try:
        entries = await redis.xrevrange(MODEL_SCORE_STREAM, count=20)
        for _eid, fields in entries:
            raw = fields.get(b"payload") or fields.get("payload")
            if raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode()
            data = json.loads(raw)
            name = data.get("model_name", "unknown")
            if name not in snapshot:
                snapshot[name] = {
                    "score": data.get("score"),
                    "confidence": data.get("confidence"),
                    "output_label": data.get("output_label"),
                    "event_id": data.get("event_id"),
                    "timestamp": data.get("timestamp"),
                }
    except Exception as exc:
        logger.debug("Model score read failed: %s", exc)
    return snapshot


def _detect_stale(snapshot: dict[str, Any], threshold_seconds: int) -> bool:
    now = datetime.now(UTC)
    for data in snapshot.values():
        if not isinstance(data, dict) or not data.get("timestamp"):
            return True
        try:
            ts = datetime.fromisoformat(str(data["timestamp"]).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if (now - ts).total_seconds() > threshold_seconds:
                return True
        except (ValueError, TypeError):
            return True
    return False


def _detect_missing(expected: list[str], snapshot: dict[str, Any]) -> list[str]:
    return [s for s in expected if s not in snapshot]


def _apply_injections(
    telemetry: dict[str, Any],
    scores: dict[str, Any],
    missing: list[str],
    stale: bool,
    corrupt: bool,
) -> tuple[dict[str, Any], dict[str, Any], list[str], bool, bool]:
    if is_active("sensor_dropout"):
        for key in list(telemetry.keys())[:2]:
            telemetry.pop(key, None)
        missing = _detect_missing(["emg", "ecg_like", "imu", "spo2_proxy"], telemetry)

    if is_active("corrupt_event"):
        corrupt = True

    if is_active("stale_telemetry"):
        stale = True
        for data in telemetry.values():
            if isinstance(data, dict):
                data["timestamp"] = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()

    if is_active("model_low_confidence"):
        for data in scores.values():
            if isinstance(data, dict):
                data["confidence"] = 0.2
                data["score"] = 0.9

    return telemetry, scores, missing, stale, corrupt


def build_initial_state(
    session_id: str,
    trace_id: str,
    telemetry: dict[str, Any],
    scores: dict[str, Any],
) -> AXONAgentState:
    """Build AXONAgentState from snapshots with failure injection applied."""
    expected_signals = ["emg", "ecg_like", "imu", "spo2_proxy"]
    missing = _detect_missing(expected_signals, telemetry)
    stale = _detect_stale(telemetry, settings.axon_stale_telemetry_seconds)
    corrupt = False

    telemetry, scores, missing, stale, corrupt = _apply_injections(
        telemetry, scores, missing, stale, corrupt
    )

    return AXONAgentState(
        session_id=session_id,
        trace_id=trace_id,
        current_time=datetime.now(UTC).isoformat(),
        telemetry_snapshot=telemetry,
        model_score_snapshot=scores,
        stale_inputs=stale,
        corrupt_inputs=corrupt,
        missing_signals=missing,
        perception_summary="",
        triage_summary="",
        safety_verdict={},
        proposed_action="continue_session",
        risk_level="nominal",
        confidence=0.85,
        requires_human_confirmation=False,
        copilot_explanation="",
        decision_event=None,
        trace_events=[],
        errors=[],
    )


async def append_trace_stream(redis: Redis | None, trace: dict) -> None:
    if redis is None:
        return
    try:
        await redis.xadd(
            AGENT_TRACE_STREAM,
            {
                "event_id": trace.get("event_id", str(uuid4())),
                "trace_id": trace.get("trace_id", ""),
                "agent_name": trace.get("agent_name", ""),
                "payload": json.dumps(trace),
            },
            maxlen=1000,
            approximate=True,
        )
    except Exception as exc:
        logger.warning("Failed to append agent trace: %s", exc)


async def append_alert_stream(redis: Redis | None, decision: DecisionEventV1) -> None:
    if redis is None or decision.risk_level not in ("high", "critical"):
        return
    try:
        await redis.xadd(
            ALERT_STREAM,
            {
                "event_id": decision.event_id,
                "decision_id": decision.decision_id,
                "risk_level": decision.risk_level,
                "payload": json.dumps(
                    {
                        "message": f"Simulated {decision.risk_level} risk alert",
                        "recommended_action": decision.recommended_action,
                        "requires_human_confirmation": decision.requires_human_confirmation,
                    }
                ),
            },
            maxlen=500,
            approximate=True,
        )
    except Exception as exc:
        logger.warning("Failed to append alert: %s", exc)


async def broadcast_trace(ws_manager: Any, trace: dict) -> None:
    _recent_traces.append(trace)
    if len(_recent_traces) > 200:
        _recent_traces.pop(0)
    await ws_manager.broadcast("agents", {"type": "agent_trace", "event": trace})


async def broadcast_decision(ws_manager: Any, decision: dict) -> None:
    global _current_decision
    _current_decision = decision
    _decision_history.append(decision)
    if len(_decision_history) > 100:
        _decision_history.pop(0)
    await ws_manager.broadcast("decisions", {"type": "decision", "event": decision})


async def broadcast_safety(ws_manager: Any) -> None:
    await ws_manager.broadcast("safety", {"type": "safety_status", "status": _safety_status})


def _update_safety_status(state: AXONAgentState) -> None:
    _safety_status.update(
        {
            "stale_telemetry": state["stale_inputs"],
            "missing_signals": state["missing_signals"],
            "low_confidence": state["confidence"] < settings.axon_safety_low_confidence_threshold,
            "high_risk": state["risk_level"] in ("high", "critical"),
            "active_injections": active_scenarios(),
        }
    )


def _llm_used_from_traces(traces: list[dict]) -> bool:
    """Return llm_used from the operator_copilot trace, if present."""
    for trace in reversed(traces):
        if trace.get("agent_name") == "operator_copilot":
            return bool(trace.get("llm_used"))
    return False


async def run_agent_graph(redis: Redis | None, ws_manager: Any) -> None:
    """Execute one agent graph cycle."""
    session_id = os.getenv("AXON_TRACE_ID", "session-synthetic-001")
    trace_id = f"trace-{uuid4().hex[:12]}"

    telemetry = await _read_stream_snapshot(redis, SENSOR_STREAMS)
    scores = await _read_model_scores(redis)

    if not telemetry and not scores:
        telemetry = {
            "emg": {
                "timestamp": datetime.now(UTC).isoformat(),
                "quality": 0.95,
                "values": [0.1, 0.12],
            },
            "imu": {
                "timestamp": datetime.now(UTC).isoformat(),
                "quality": 0.92,
                "values": [0.0, 0.1],
            },
        }
        scores = {
            "emg_anomaly": {
                "score": 0.1,
                "confidence": 0.9,
                "output_label": "normal",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }

    state = build_initial_state(session_id, trace_id, telemetry, scores)
    graph = get_compiled_graph_cached()
    result = graph.invoke(state)

    _update_safety_status(result)

    for trace in result.get("trace_events", []):
        await append_trace_stream(redis, trace)
        await broadcast_trace(ws_manager, trace)

    decision_data = result.get("decision_event")
    if decision_data:
        decision = DecisionEventV1.model_validate(decision_data)
        if result.get("copilot_explanation") and not decision.requires_human_confirmation:
            decision.rationale = (
                f"{decision.rationale} | Copilot: {result['copilot_explanation'][:200]}"
            )
            decision.llm_used = _llm_used_from_traces(result.get("trace_events", []))
        await append_decision_stream(redis, decision)
        await append_alert_stream(redis, decision)

        if decision.requires_human_confirmation:
            await store_pending_decision(redis, decision)

        await broadcast_decision(ws_manager, decision.model_dump(mode="json"))

    await broadcast_safety(ws_manager)


async def agent_loop(redis: Redis | None, ws_manager: Any) -> None:
    """Background agent loop with concurrency guard."""
    global _graph_running
    load_rag_documents()
    await load_pending_decisions(redis)

    while True:
        await asyncio.sleep(LOOP_INTERVAL)
        evict_expired_injections()
        await expire_pending_decisions(
            redis,
            settings.axon_hitl_expiry_seconds,
            broadcast_fn=lambda d: broadcast_decision(ws_manager, d.model_dump(mode="json")),
        )
        if _graph_running:
            logger.warning(
                json.dumps({"event": "agent_loop_skipped", "reason": "previous_run_in_progress"})
            )
            continue
        _graph_running = True
        try:
            await run_agent_graph(redis, ws_manager)
        except Exception as exc:
            logger.error(json.dumps({"event": "agent_graph_error", "error": str(exc)}))
        finally:
            _graph_running = False


async def agent_loop_tick(redis: Redis | None, ws_manager: Any) -> None:
    """Single tick for testing concurrent guard."""
    global _graph_running
    evict_expired_injections()
    if _graph_running:
        logger.warning(
            json.dumps({"event": "agent_loop_skipped", "reason": "previous_run_in_progress"})
        )
        return
    _graph_running = True
    try:
        await run_agent_graph(redis, ws_manager)
    finally:
        _graph_running = False
