"""AXON event contracts (Pydantic v2)."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class _EventBase(BaseModel):
    """Shared fields for all AXON events."""

    schema_version: Literal["v1"] = "v1"
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_id: str
    source: str

    @field_validator("trace_id", "source")
    @classmethod
    def non_empty_string(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()


SignalType = Literal[
    "emg",
    "ecg_like",
    "imu",
    "spo2_proxy",
    "robot_state",
    "environment",
]

RiskLevel = Literal["nominal", "low", "medium", "high", "critical"]

RecommendedAction = Literal[
    "continue_session",
    "reduce_intensity",
    "pause_simulation",
    "request_operator_check",
    "escalate_simulated_alert",
    "ignore_corrupt_event",
    "hold_for_more_data",
]

DecisionStatus = Literal[
    "proposed",
    "pending_human_confirmation",
    "confirmed",
    "rejected",
    "simulated_executed",
    "expired",
]

AgentName = Literal[
    "perception_agent",
    "triage_agent",
    "safety_agent",
    "action_recommendation_agent",
    "operator_copilot",
    "research_rag_agent",
]

AgentStage = Literal[
    "started",
    "completed",
    "skipped",
    "failed",
    "interrupted_for_human",
]


class HumanResponseV1(BaseModel):
    """Operator human-in-the-loop response."""

    operator_id: str
    response: Literal["confirmed", "rejected"]
    note: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SensorEventV1(_EventBase):
    """Synthetic sensor telemetry event."""

    signal_type: SignalType
    unit: str
    values: list[float]
    quality: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("unit")
    @classmethod
    def unit_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("unit must not be empty")
        return value.strip()

    @field_validator("values")
    @classmethod
    def values_not_empty(cls, value: list[float]) -> list[float]:
        if not value:
            raise ValueError("values must not be empty")
        return value


class DecisionEventV1(_EventBase):
    """Agent orchestration decision event (Phase 3)."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    source_service: str = "axon-api"
    input_window_start: datetime
    input_window_end: datetime
    risk_level: RiskLevel
    recommended_action: RecommendedAction
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_confirmation: bool
    status: DecisionStatus = "proposed"
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    contributing_signals: list[str] = Field(default_factory=list)
    model_score_refs: list[str] = Field(default_factory=list)
    safety_constraints: list[str] = Field(default_factory=list)
    llm_used: bool = False
    llm_mode: str = "mock"
    llm_provider: str = "mock"
    created_by_agent: str = "action_recommendation_agent"
    human_response: HumanResponseV1 | None = None

    @field_validator("rationale", "session_id", "source_service")
    @classmethod
    def decision_strings_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()


class ModelScoreEventV1(_EventBase):
    """Edge inference model score event."""

    model_name: str
    model_version: str
    score: float
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    input_event_id: str
    output_label: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model_name", "model_version", "input_event_id", "output_label")
    @classmethod
    def model_strings_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()


class AgentTraceEventV1(_EventBase):
    """LangGraph agent step trace event (Phase 3)."""

    span_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_span_id: str | None = None
    session_id: str
    agent_name: AgentName
    stage: AgentStage
    input_refs: list[str] = Field(default_factory=list)
    output_summary: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_level: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
    llm_used: bool = False
    duration_ms: float = Field(ge=0.0, default=0.0)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("output_summary", "session_id")
    @classmethod
    def trace_strings_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()


class HealthEventV1(_EventBase):
    """Component health and latency event."""

    component: str
    status: Literal["ok", "degraded", "down"]
    latency_ms: float = Field(ge=0.0)
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("component", "message")
    @classmethod
    def health_strings_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()


class DriftEventV1(_EventBase):
    """Sliding-window confidence drift event (Phase 4)."""

    session_id: str
    signal_type: Literal["emg", "imu", "fusion", "all"]
    detector_version: str = "sliding_window_v1"
    drift_score: float | None = None
    threshold: float
    drift_status: Literal["nominal", "drift_detected", "insufficient_data"]
    evidence_window: int
    mean_confidence: float | None = None
    recommendation: Literal["continue_monitoring", "evaluate_candidate_model"]
    synthetic_only: bool = True
    safety_notes: str = (
        "Simulated drift detection on synthetic signals. "
        "No clinical inference. No automatic model replacement."
    )

    @field_validator("session_id")
    @classmethod
    def session_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("session_id must not be empty")
        return value.strip()
