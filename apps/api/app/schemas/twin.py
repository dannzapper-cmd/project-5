"""Phase 5 Digital Twin state and command contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from apps.api.app.schemas.events import RiskLevel

RobotMode = Literal["idle", "assisting", "paused", "alert", "degraded", "recovery"]
SensorNodeKey = Literal["emg", "ecg", "imu", "spo2"]
SensorNodeStatus = Literal["active", "stale", "dropout", "corrupt", "degraded"]
SafetyEnvelopeStatus = Literal["nominal", "warning", "blocked", "pending_hitl"]
ROS2BridgeConnectionStatus = Literal["connected", "simulated", "offline"]
TwinCommandName = Literal["pause", "resume", "request_safety_stop", "set_assist_mode"]
TwinCommandStatus = Literal["accepted", "rejected", "blocked", "pending_hitl"]
AssistMode = Literal["idle", "assist_low", "assist_medium", "assist_high"]


class RobotPoseV1(BaseModel):
    """2D-lite robot pose for dashboard mirror."""

    schema_version: Literal["v1"] = "v1"
    x: float = 0.0
    y: float = 0.0
    orientation_deg: float = 0.0


class RobotStateV1(BaseModel):
    """Robot / exoskeleton operational state."""

    schema_version: Literal["v1"] = "v1"
    pose: RobotPoseV1 = Field(default_factory=RobotPoseV1)
    joint_angle_deg: float | None = None
    mode: RobotMode = "idle"
    battery_pct: float | None = None
    load_pct: float | None = None
    latency_ms: float | None = None


class SensorNodeStateV1(BaseModel):
    """Per-sensor node mirror state."""

    schema_version: Literal["v1"] = "v1"
    status: SensorNodeStatus = "dropout"
    latest_value_summary: str = "—"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    trace_id: str | None = None
    last_updated: datetime | None = None


class FusionStateV1(BaseModel):
    """Fused operational confidence and anomaly indicators."""

    schema_version: Literal["v1"] = "v1"
    global_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: RiskLevel = "nominal"
    active_anomalies: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)
    corrupt_indicators: list[str] = Field(default_factory=list)


class AgentStateV1(BaseModel):
    """Active agent and decision trace linkage."""

    schema_version: Literal["v1"] = "v1"
    active_agent: str | None = None
    last_decision: str | None = None
    last_action: str | None = None
    trace_id: str | None = None
    agent_trace_id: str | None = None
    hitl_pending: bool = False


class SafetyStateV1(BaseModel):
    """Safety envelope and action gating."""

    schema_version: Literal["v1"] = "v1"
    envelope_status: SafetyEnvelopeStatus = "nominal"
    allowed_actions: list[str] = Field(default_factory=list)
    proposed_action: str | None = None
    blocked_action: str | None = None
    blocked_reason: str | None = None


class ROS2BridgeStatusV1(BaseModel):
    """ROS2 thin adapter connectivity."""

    schema_version: Literal["v1"] = "v1"
    status: ROS2BridgeConnectionStatus = "offline"
    last_topic_publish: datetime | None = None
    last_command_status: str | None = None


class DigitalTwinStateV1(BaseModel):
    """Versioned digital twin snapshot derived from live AXON pipeline state."""

    schema_version: Literal["v1"] = "v1"
    robot_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    robot_state: RobotStateV1
    sensor_nodes: dict[SensorNodeKey, SensorNodeStateV1]
    fusion: FusionStateV1
    agents: AgentStateV1
    safety: SafetyStateV1
    ros2_bridge: ROS2BridgeStatusV1


class TwinCommandRequestV1(BaseModel):
    """Safe robot/twin command request."""

    schema_version: Literal["v1"] = "v1"
    command: TwinCommandName
    requested_by: str
    reason: str | None = None
    assist_mode: AssistMode | None = None


class TwinCommandResponseV1(BaseModel):
    """Command handling outcome with trace linkage."""

    schema_version: Literal["v1"] = "v1"
    status: TwinCommandStatus
    command: str
    reason: str | None = None
    trace_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
