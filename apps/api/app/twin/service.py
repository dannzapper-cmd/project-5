# AXON Phase 5 Digital Twin Integration Points
# Consuming Redis Streams:
#   - axon:v1:stream:sensors:emg
#   - axon:v1:stream:sensors:ecg_like
#   - axon:v1:stream:sensors:imu
#   - axon:v1:stream:sensors:spo2_proxy
#   - axon:v1:stream:robot_state
#   - axon:v1:stream:model_scores
#   - axon:v1:stream:agent_traces
#   - axon:v1:stream:decisions
#   - axon:v1:stream:alerts
# Consuming in-process agent/safety state:
#   - apps.api.app.agents.service (safety status, traces, decisions)
# Emitting:
#   - Redis Stream: axon:v1:stream:fusion (fusion snapshot)
#   - WebSocket channel: twin (/ws/v1/twin)
# MQTT topics (indirect via Redis ingest from generators/replay):
#   - axon/v1/sensors/emg/{node_id}
#   - axon/v1/sensors/ecg-like/{node_id}
#   - axon/v1/sensors/imu/{node_id}
#   - axon/v1/sensors/spo2-proxy/{node_id}
#   - axon/v1/robot/state/{robot_id}

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from redis.asyncio import Redis

from apps.api.app.agents.service import (
    get_current_decision,
    get_recent_traces,
    get_safety_status,
)
from apps.api.app.core.config import settings
from apps.api.app.schemas.twin import (
    AgentStateV1,
    AssistMode,
    DigitalTwinStateV1,
    FusionStateV1,
    RobotPoseV1,
    RobotStateV1,
    ROS2BridgeStatusV1,
    SafetyStateV1,
    SensorNodeKey,
    SensorNodeStateV1,
    SensorNodeStatus,
    TwinCommandRequestV1,
    TwinCommandResponseV1,
    TwinCommandStatus,
)
from apps.api.app.telemetry.model_score_streams import MODEL_SCORE_STREAM
from apps.api.app.telemetry.topic_router import ROBOT_STREAM, SENSOR_STREAMS

logger = logging.getLogger(__name__)

FUSION_STREAM = "axon:v1:stream:fusion"
ROS2_HEARTBEAT_KEY = "axon:v1:ros2_bridge:heartbeat"

SENSOR_KEY_MAP: dict[str, SensorNodeKey] = {
    "emg": "emg",
    "ecg_like": "ecg",
    "imu": "imu",
    "spo2_proxy": "spo2",
}
NOMINAL_MODEL_LABELS = {"normal", "nominal", "stable_motion"}

TWIN_BROADCAST_HZ = max(2, min(10, int(os.getenv("TWIN_BROADCAST_HZ", "5"))))
SENSOR_STALE_TTL_SECONDS = max(3, min(10, int(os.getenv("SENSOR_STALE_TTL_SECONDS", "5"))))
SENSOR_DROPOUT_TTL_SECONDS = max(10, min(30, int(os.getenv("SENSOR_DROPOUT_TTL_SECONDS", "15"))))

_latest_twin: DigitalTwinStateV1 | None = None
_session_paused: bool = False
_safety_stop_active: bool = False
_assist_mode: AssistMode = "assist_medium"
_last_ros2_heartbeat: datetime | None = None
_last_ros2_command_status: str | None = None
_twin_trace_id: str = f"twin-{uuid4().hex[:12]}"


def get_latest_twin_state() -> DigitalTwinStateV1 | None:
    return _latest_twin


def get_twin_service_status() -> dict[str, Any]:
    return {
        "running": _latest_twin is not None,
        "broadcast_hz": TWIN_BROADCAST_HZ,
        "sensor_stale_ttl_seconds": SENSOR_STALE_TTL_SECONDS,
        "sensor_dropout_ttl_seconds": SENSOR_DROPOUT_TTL_SECONDS,
        "session_paused": _session_paused,
        "safety_stop_active": _safety_stop_active,
        "assist_mode": _assist_mode,
        "last_broadcast": _latest_twin.timestamp.isoformat() if _latest_twin else None,
    }


def record_ros2_heartbeat(command_status: str | None = None) -> None:
    global _last_ros2_heartbeat, _last_ros2_command_status
    _last_ros2_heartbeat = datetime.now(UTC)
    if command_status:
        _last_ros2_command_status = command_status


def _parse_stream_payload(fields: dict) -> dict[str, Any] | None:
    raw = fields.get(b"payload") or fields.get("payload")
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    return json.loads(raw)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts
    except (ValueError, TypeError):
        return None


def _sensor_status(
    last_updated: datetime | None,
    quality: float,
    now: datetime,
) -> SensorNodeStatus:
    if last_updated is None:
        return "dropout"
    age = (now - last_updated).total_seconds()
    if age >= SENSOR_DROPOUT_TTL_SECONDS:
        return "dropout"
    if age >= SENSOR_STALE_TTL_SECONDS:
        return "stale"
    if quality < 0.3:
        return "corrupt"
    if quality < 0.6:
        return "degraded"
    return "active"


def _value_summary(signal: str, values: list[float] | None) -> str:
    if not values:
        return "—"
    if signal == "robot_state" and len(values) >= 4:
        return (
            f"battery={values[0]:.1f}% joint={values[1]:.1f}° "
            f"load={values[2]:.1f}% mode={values[3]:.0f}"
        )
    latest = values[-1]
    return f"{latest:.3f}" if isinstance(latest, float) else str(latest)


async def _read_sensor_snapshots(redis: Redis | None) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    if redis is None:
        return snapshots
    streams = SENSOR_STREAMS + [ROBOT_STREAM]
    for stream in streams:
        try:
            entries = await redis.xrevrange(stream, count=1)
            if not entries:
                continue
            _eid, fields = entries[0]
            data = _parse_stream_payload(fields)
            if not data:
                continue
            signal = data.get("signal_type") or stream.split(":")[-1]
            snapshots[signal] = data
        except Exception as exc:
            logger.debug("Twin sensor read failed for %s: %s", stream, exc)
    return snapshots


async def _read_model_scores(redis: Redis | None) -> dict[str, Any]:
    scores: dict[str, Any] = {}
    if redis is None:
        return scores
    try:
        entries = await redis.xrevrange(MODEL_SCORE_STREAM, count=20)
        for _eid, fields in entries:
            data = _parse_stream_payload(fields)
            if not data:
                continue
            name = data.get("model_name", "unknown")
            if name not in scores:
                scores[name] = data
    except Exception as exc:
        logger.debug("Twin model score read failed: %s", exc)
    return scores


def _compute_global_confidence(
    sensor_nodes: dict[SensorNodeKey, SensorNodeStateV1],
    model_scores: dict[str, Any],
) -> float:
    confidences: list[float] = []
    for node in sensor_nodes.values():
        if node.status in ("active", "degraded"):
            confidences.append(node.confidence)
    for score in model_scores.values():
        conf = score.get("confidence")
        if conf is not None:
            confidences.append(float(conf))
    if not confidences:
        return 0.0
    return round(sum(confidences) / len(confidences), 3)


def _derive_risk_level(
    global_confidence: float,
    sensor_nodes: dict[SensorNodeKey, SensorNodeStateV1],
    decision: dict | None,
    safety: dict[str, Any],
) -> str:
    if safety.get("high_risk"):
        return "high"
    decision_risk = str(decision["risk_level"]) if decision and decision.get("risk_level") else None
    if decision_risk in ("high", "critical"):
        return decision_risk
    if any(n.status in ("dropout", "corrupt") for n in sensor_nodes.values()):
        return "medium"
    if global_confidence < 0.4 and any(
        n.status in ("stale", "dropout") for n in sensor_nodes.values()
    ):
        return "medium"
    if decision_risk == "medium":
        return decision_risk
    if any(n.status in ("stale", "degraded") for n in sensor_nodes.values()):
        return "low"
    if decision_risk:
        return decision_risk
    if global_confidence < settings.axon_safety_low_confidence_threshold:
        return "low"
    return "nominal"


def _derive_robot_mode(
    global_confidence: float,
    sensor_nodes: dict[SensorNodeKey, SensorNodeStateV1],
    risk_level: str,
    decision: dict | None,
) -> str:
    if _safety_stop_active or _session_paused:
        return "paused"
    if decision and decision.get("status") == "pending_human_confirmation":
        return "paused"
    if any(n.status in ("dropout", "corrupt") for n in sensor_nodes.values()):
        return "degraded"
    stale_or_dropout = any(n.status in ("stale", "dropout") for n in sensor_nodes.values())
    if global_confidence < 0.4 and stale_or_dropout:
        return "degraded"
    if risk_level in ("high", "critical"):
        return "alert"
    if risk_level == "medium":
        return "degraded"
    if _assist_mode == "idle":
        return "idle"
    if (
        not _safety_stop_active
        and not _session_paused
        and risk_level in ("nominal", "low")
    ):
        return "assisting"
    return "assisting"


def _ros2_status(now: datetime) -> ROS2BridgeStatusV1:
    if _last_ros2_heartbeat is None:
        return ROS2BridgeStatusV1(status="offline")
    age = (now - _last_ros2_heartbeat).total_seconds()
    if age > 30:
        return ROS2BridgeStatusV1(status="offline", last_command_status=_last_ros2_command_status)
    return ROS2BridgeStatusV1(
        status="connected",
        last_topic_publish=_last_ros2_heartbeat,
        last_command_status=_last_ros2_command_status,
    )


def _build_sensor_nodes(
    snapshots: dict[str, dict[str, Any]],
    model_scores: dict[str, Any],
    now: datetime,
) -> dict[SensorNodeKey, SensorNodeStateV1]:
    nodes: dict[SensorNodeKey, SensorNodeStateV1] = {}
    for signal, key in SENSOR_KEY_MAP.items():
        data = snapshots.get(signal, {})
        ts = _parse_timestamp(data.get("timestamp"))
        quality = float(data.get("quality", 0.0))
        status = _sensor_status(ts, quality, now)
        values = data.get("values", [])
        confidence = quality
        for score in model_scores.values():
            meta = score.get("metadata") or {}
            if meta.get("input_signal") == signal or meta.get("signal_type") == signal:
                confidence = max(confidence, float(score.get("confidence", quality)))
        nodes[key] = SensorNodeStateV1(
            status=status,
            latest_value_summary=_value_summary(signal, values),
            confidence=round(confidence, 3),
            trace_id=data.get("trace_id"),
            last_updated=ts,
        )
    return nodes


def _build_safety_state(
    decision: dict | None,
    safety: dict[str, Any],
    risk_level: str,
) -> SafetyStateV1:
    allowed = ["continue_session", "reduce_intensity"]
    proposed = decision.get("recommended_action") if decision else "continue_session"
    blocked_action = None
    blocked_reason = None
    envelope = "nominal"

    if decision and decision.get("requires_human_confirmation"):
        envelope = "pending_hitl"
        blocked_action = proposed
        blocked_reason = "Simulated high-risk action requires operator confirmation (HITL)."
        allowed = ["request_operator_check"]
    elif _safety_stop_active:
        envelope = "blocked"
        blocked_action = proposed
        blocked_reason = "Safety stop active — resume only after operator clearance."
        allowed = []
    elif _session_paused:
        envelope = "warning"
        blocked_action = "continue_session"
        blocked_reason = "Session paused by operator or command."
        allowed = ["resume"]
    elif safety.get("high_risk") or risk_level in ("high", "critical"):
        envelope = "warning"
        blocked_reason = "Elevated simulated operational risk."
    elif safety.get("stale_telemetry") or safety.get("missing_signals"):
        envelope = "warning"
        blocked_reason = "Stale or missing synthetic telemetry."

    return SafetyStateV1(
        envelope_status=envelope,
        allowed_actions=allowed,
        proposed_action=proposed,
        blocked_action=blocked_action,
        blocked_reason=blocked_reason,
    )


def _build_agent_state(decision: dict | None, traces: list[dict]) -> AgentStateV1:
    active_agent = None
    agent_trace_id = None
    if traces:
        latest = traces[-1]
        active_agent = latest.get("agent_name")
        agent_trace_id = latest.get("event_id")
    return AgentStateV1(
        active_agent=active_agent,
        last_decision=decision.get("decision_id") if decision else None,
        last_action=decision.get("recommended_action") if decision else None,
        trace_id=decision.get("trace_id") if decision else _twin_trace_id,
        agent_trace_id=agent_trace_id,
        hitl_pending=bool(decision and decision.get("status") == "pending_human_confirmation"),
    )


async def build_twin_state(redis: Redis | None) -> DigitalTwinStateV1:
    """Build deterministic twin snapshot from live AXON pipeline state."""
    now = datetime.now(UTC)
    robot_id = os.getenv("AXON_ROBOT_ID", "rehab-robot-01")
    session_id = os.getenv("AXON_TRACE_ID", "session-synthetic-001")

    snapshots = await _read_sensor_snapshots(redis)
    model_scores = await _read_model_scores(redis)
    safety = get_safety_status()
    decision = get_current_decision()
    traces = get_recent_traces(5)

    sensor_nodes = _build_sensor_nodes(snapshots, model_scores, now)
    global_confidence = _compute_global_confidence(sensor_nodes, model_scores)
    risk_level = _derive_risk_level(global_confidence, sensor_nodes, decision, safety)

    anomalies: list[str] = []
    missing: list[str] = []
    corrupt: list[str] = []
    for key, node in sensor_nodes.items():
        if node.status == "dropout":
            missing.append(key)
        elif node.status == "stale":
            anomalies.append(f"{key}_stale")
        elif node.status == "corrupt":
            corrupt.append(key)
        elif node.status == "degraded":
            anomalies.append(f"{key}_degraded")
    for score in model_scores.values():
        label = score.get("output_label", "")
        if label and label not in NOMINAL_MODEL_LABELS:
            anomalies.append(f"model:{score.get('model_name')}:{label}")

    robot_snap = snapshots.get("robot_state", {})
    robot_values = robot_snap.get("values", [85.0, 30.0, 20.0, 1.0])
    joint_angle = float(robot_values[1]) if len(robot_values) > 1 else 30.0
    battery = float(robot_values[0]) if robot_values else None
    load_pct = float(robot_values[2]) if len(robot_values) > 2 else None
    mode_code = float(robot_values[3]) if len(robot_values) > 3 else 1.0

    robot_mode = _derive_robot_mode(global_confidence, sensor_nodes, risk_level, decision)
    if mode_code >= 2.0 and robot_mode == "assisting":
        robot_mode = "idle"

    pose = RobotPoseV1(
        x=round(joint_angle / 90.0, 3),
        y=round((load_pct or 20.0) / 100.0, 3),
        orientation_deg=round(joint_angle, 2),
    )

    avg_latency = None
    latencies = [
        float(s.get("latency_ms", 0))
        for s in model_scores.values()
        if s.get("latency_ms")
    ]
    if latencies:
        avg_latency = round(sum(latencies) / len(latencies), 2)

    twin = DigitalTwinStateV1(
        robot_id=robot_id,
        session_id=session_id,
        timestamp=now,
        robot_state=RobotStateV1(
            pose=pose,
            joint_angle_deg=joint_angle,
            mode=robot_mode,  # type: ignore[arg-type]
            battery_pct=battery,
            load_pct=load_pct,
            latency_ms=avg_latency,
        ),
        sensor_nodes=sensor_nodes,
        fusion=FusionStateV1(
            global_confidence=global_confidence,
            risk_level=risk_level,  # type: ignore[arg-type]
            active_anomalies=anomalies,
            missing_signals=missing,
            corrupt_indicators=corrupt,
        ),
        agents=_build_agent_state(decision, traces),
        safety=_build_safety_state(decision, safety, risk_level),
        ros2_bridge=_ros2_status(now),
    )
    return twin


async def _append_fusion_stream(redis: Redis | None, twin: DigitalTwinStateV1) -> None:
    if redis is None:
        return
    try:
        payload = twin.fusion.model_dump(mode="json")
        payload["session_id"] = twin.session_id
        payload["trace_id"] = twin.agents.trace_id or _twin_trace_id
        payload["timestamp"] = twin.timestamp.isoformat()
        await redis.xadd(
            FUSION_STREAM,
            {
                "event_id": str(uuid4()),
                "trace_id": payload["trace_id"],
                "payload": json.dumps(payload),
            },
            maxlen=500,
            approximate=True,
        )
    except Exception as exc:
        logger.debug("Fusion stream append failed: %s", exc)


async def handle_twin_command(request: TwinCommandRequestV1) -> TwinCommandResponseV1:
    """Validate and apply safe twin commands with safety/HITL boundaries."""
    global _session_paused, _safety_stop_active, _assist_mode, _twin_trace_id

    trace_id = f"cmd-{uuid4().hex[:12]}"
    decision = get_current_decision()
    safety = get_safety_status()
    status: TwinCommandStatus = "accepted"
    reason: str | None = None

    if request.command == "pause":
        _session_paused = True
        reason = "Session paused by operator command."

    elif request.command == "resume":
        if _safety_stop_active:
            status = "blocked"
            reason = "Cannot resume while safety stop is active."
        elif decision and decision.get("status") == "pending_human_confirmation":
            status = "pending_hitl"
            reason = "HITL confirmation required before resume."
        elif safety.get("high_risk"):
            status = "blocked"
            reason = "Elevated simulated risk blocks automatic resume."
        else:
            _session_paused = False
            if _safety_stop_active:
                _safety_stop_active = False
            reason = "Session resumed."

    elif request.command == "request_safety_stop":
        _safety_stop_active = True
        _session_paused = True
        if decision and decision.get("requires_human_confirmation"):
            status = "pending_hitl"
            reason = "Safety stop applied; operator confirmation may be required to clear."
        else:
            reason = "Safety stop accepted — session paused."

    elif request.command == "set_assist_mode":
        if not request.assist_mode:
            status = "rejected"
            reason = "assist_mode is required for set_assist_mode."
        elif _safety_stop_active or _session_paused:
            status = "blocked"
            reason = "Cannot change assist mode while paused or safety-stopped."
        elif safety.get("high_risk") and request.assist_mode in ("assist_high",):
            status = "blocked"
            reason = "High assist mode blocked under elevated simulated risk."
        else:
            _assist_mode = request.assist_mode
            reason = f"Assist mode set to {request.assist_mode}."

    _twin_trace_id = trace_id
    return TwinCommandResponseV1(
        status=status,
        command=request.command,
        reason=reason,
        trace_id=trace_id,
    )


async def twin_broadcast_loop(redis: Redis | None, ws_manager: Any) -> None:
    """Background loop: build twin state and broadcast at TWIN_BROADCAST_HZ."""
    global _latest_twin
    interval = 1.0 / TWIN_BROADCAST_HZ
    while True:
        try:
            twin = await build_twin_state(redis)
            _latest_twin = twin
            await _append_fusion_stream(redis, twin)
            await ws_manager.broadcast(
                "twin",
                {"type": "twin_state", "state": twin.model_dump(mode="json")},
            )
        except Exception as exc:
            logger.warning("Twin broadcast error: %s", exc)
        await asyncio.sleep(interval)
