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
    """Agent or rules-engine decision event."""

    decision_type: str
    risk_level: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: str
    requires_human_confirmation: bool
    rationale: str
    related_event_ids: list[str] = Field(default_factory=list)

    @field_validator("decision_type", "recommended_action", "rationale")
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
    """LangGraph agent step trace event."""

    agent_name: str
    step_name: str
    input_summary: str
    output_summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    tool_calls: list[str] = Field(default_factory=list)
    requires_human_review: bool
    related_event_ids: list[str] = Field(default_factory=list)

    @field_validator("agent_name", "step_name", "input_summary", "output_summary")
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
