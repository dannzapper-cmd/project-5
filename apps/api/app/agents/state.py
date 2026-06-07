"""AXONAgentState TypedDict for LangGraph StateGraph."""

from typing import TypedDict


class AXONAgentState(TypedDict):
    """Stateful fields for the Phase 3 agent orchestration graph."""

    session_id: str
    trace_id: str
    current_time: str
    telemetry_snapshot: dict
    model_score_snapshot: dict
    stale_inputs: bool
    corrupt_inputs: bool
    missing_signals: list[str]
    perception_summary: str
    triage_summary: str
    safety_verdict: dict
    proposed_action: str
    risk_level: str
    confidence: float
    requires_human_confirmation: bool
    copilot_explanation: str
    decision_event: dict | None
    trace_events: list[dict]
    errors: list[str]
