"""LangGraph node functions for Phase 3 agent orchestration."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from apps.api.app.agents.safety import apply_safety_rules, build_safety_rationale
from apps.api.app.agents.state import AXONAgentState
from apps.api.app.core.config import settings
from apps.api.app.langchain.provider import MockCopilotRunnable, get_chat_model
from apps.api.app.langchain.rag import get_rag_docs
from apps.api.app.langchain.tools import (
    draft_operator_explanation,
    get_latest_model_scores,
    get_recent_telemetry_summary,
    lookup_operational_runbook,
    lookup_safety_policy,
)
from apps.api.app.schemas.events import AgentTraceEventV1, DecisionEventV1

SOURCE = "axon-api"
EXPECTED_CONTRIBUTING_SIGNALS = ("emg", "ecg_like", "imu", "spo2_proxy")


def _contributing_signals(state: AXONAgentState) -> list[str]:
    """Return synthetic signals present in telemetry and used in analysis."""
    missing = set(state.get("missing_signals") or [])
    telemetry = state.get("telemetry_snapshot") or {}
    return [
        signal
        for signal in EXPECTED_CONTRIBUTING_SIGNALS
        if signal in telemetry and signal not in missing
    ]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _make_trace(
    state: AXONAgentState,
    agent_name: str,
    stage: str,
    output_summary: str,
    *,
    confidence: float | None = None,
    risk_level: str | None = None,
    tool_calls: list[str] | None = None,
    llm_used: bool = False,
    duration_ms: float = 0.0,
    error: str | None = None,
    input_refs: list[str] | None = None,
) -> dict:
    event = AgentTraceEventV1(
        trace_id=state["trace_id"],
        source=SOURCE,
        session_id=state["session_id"],
        agent_name=agent_name,  # type: ignore[arg-type]
        stage=stage,  # type: ignore[arg-type]
        input_refs=input_refs or [],
        output_summary=output_summary,
        confidence=confidence,
        risk_level=risk_level,
        tool_calls=tool_calls or [],
        llm_used=llm_used,
        duration_ms=duration_ms,
        error=error,
    )
    return event.model_dump(mode="json")


def perception_agent(state: AXONAgentState) -> dict:
    """Summarize telemetry/model scores; detect stale/corrupt/missing inputs."""
    t0 = time.monotonic()
    tool_calls = ["get_recent_telemetry_summary", "get_latest_model_scores"]
    tel_summary = get_recent_telemetry_summary(state["telemetry_snapshot"])
    score_summary = get_latest_model_scores(state["model_score_snapshot"])

    missing = state.get("missing_signals", [])
    stale = state.get("stale_inputs", False)
    corrupt = state.get("corrupt_inputs", False)

    parts = [tel_summary, score_summary]
    if missing:
        parts.append(f"Missing synthetic signals: {', '.join(missing)}")
    if stale:
        parts.append("Stale synthetic telemetry detected.")
    if corrupt:
        parts.append("Corrupt synthetic event flagged.")

    summary = " | ".join(parts)
    duration_ms = (time.monotonic() - t0) * 1000
    trace = _make_trace(
        state,
        "perception_agent",
        "completed",
        summary[:500],
        tool_calls=tool_calls,
        duration_ms=duration_ms,
        input_refs=list(state["telemetry_snapshot"].keys()),
    )
    return {
        "perception_summary": summary,
        "trace_events": state.get("trace_events", []) + [trace],
    }


def triage_agent(state: AXONAgentState) -> dict:
    """Assign preliminary risk and confidence from snapshots and rules."""
    t0 = time.monotonic()
    confidence = 0.85
    risk_level = "nominal"
    proposed_action = "continue_session"

    scores = state.get("model_score_snapshot", {})
    max_score = 0.0
    min_conf = 1.0
    for _name, data in scores.items():
        if isinstance(data, dict):
            max_score = max(max_score, float(data.get("score", 0)))
            min_conf = min(min_conf, float(data.get("confidence", 1)))

    if state.get("corrupt_inputs"):
        risk_level = "medium"
        confidence = 0.3
    elif state.get("missing_signals"):
        risk_level = "low"
        confidence = max(0.4, min_conf * 0.8)
    elif max_score >= 0.8:
        risk_level = "high"
        confidence = min_conf
        proposed_action = "pause_simulation"
    elif max_score >= 0.5:
        risk_level = "medium"
        confidence = min_conf
        proposed_action = "reduce_intensity"
    elif state.get("stale_inputs"):
        risk_level = "low"
        confidence = max(0.5, min_conf * 0.9)

    if min_conf < settings.axon_safety_low_confidence_threshold:
        confidence = min(confidence, min_conf)

    summary = (
        f"Triage: simulated risk={risk_level}, confidence={confidence:.2f}, "
        f"max_score={max_score:.2f}, stale={state.get('stale_inputs')}"
    )
    duration_ms = (time.monotonic() - t0) * 1000
    trace = _make_trace(
        state,
        "triage_agent",
        "completed",
        summary,
        confidence=confidence,
        risk_level=risk_level,
        tool_calls=["triage_rules"],
        duration_ms=duration_ms,
    )
    return {
        "triage_summary": summary,
        "risk_level": risk_level,
        "confidence": confidence,
        "proposed_action": proposed_action,
        "trace_events": state.get("trace_events", []) + [trace],
    }


def safety_agent(state: AXONAgentState) -> dict:
    """Apply deterministic safety rules — no LLM."""
    t0 = time.monotonic()
    verdict = apply_safety_rules(state)
    rationale = build_safety_rationale(state)
    duration_ms = (time.monotonic() - t0) * 1000
    trace = _make_trace(
        state,
        "safety_agent",
        "completed",
        f"Safety verdict: action={verdict['proposed_action']}, "
        f"HITL={verdict['requires_human_confirmation']}",
        confidence=state.get("confidence"),
        risk_level=verdict.get("risk_level"),
        tool_calls=["lookup_safety_policy"],
        duration_ms=duration_ms,
    )
    safety_verdict = dict(verdict.get("safety_verdict", {}))
    safety_verdict["rationale"] = rationale
    safety_verdict["safety_constraints"] = verdict.get("safety_constraints", [])
    return {
        "proposed_action": verdict["proposed_action"],
        "requires_human_confirmation": verdict["requires_human_confirmation"],
        "risk_level": verdict["risk_level"],
        "safety_verdict": safety_verdict,
        "trace_events": state.get("trace_events", []) + [trace],
    }


def action_recommendation_agent(state: AXONAgentState) -> dict:
    """Build DecisionEventV1 from safety verdict."""
    t0 = time.monotonic()
    now = datetime.now(UTC)
    rationale = state.get("safety_verdict", {}).get("rationale") or draft_operator_explanation(
        dict(state)
    )
    safety_constraints = state.get("safety_verdict", {}).get("safety_constraints", [])

    status = "pending_human_confirmation" if state["requires_human_confirmation"] else "proposed"
    if state["requires_human_confirmation"]:
        status = "pending_human_confirmation"

    decision = DecisionEventV1(
        trace_id=state["trace_id"],
        source=SOURCE,
        session_id=state["session_id"],
        source_service=SOURCE,
        input_window_start=now,
        input_window_end=now,
        risk_level=state["risk_level"],  # type: ignore[arg-type]
        recommended_action=state["proposed_action"],  # type: ignore[arg-type]
        confidence=state["confidence"],
        requires_human_confirmation=state["requires_human_confirmation"],
        status=status,  # type: ignore[arg-type]
        rationale=rationale,
        evidence_refs=[f"trace:{state['trace_id']}"],
        contributing_signals=_contributing_signals(state),
        model_score_refs=list(state.get("model_score_snapshot", {}).keys()),
        safety_constraints=safety_constraints if isinstance(safety_constraints, list) else [],
        llm_used=False,
        llm_mode=settings.axon_llm_mode,
        llm_provider=settings.axon_llm_provider,
        created_by_agent="action_recommendation_agent",
    )
    duration_ms = (time.monotonic() - t0) * 1000
    trace = _make_trace(
        state,
        "action_recommendation_agent",
        "interrupted_for_human" if state["requires_human_confirmation"] else "completed",
        f"Decision: {decision.recommended_action}, status={decision.status}",
        confidence=decision.confidence,
        risk_level=decision.risk_level,
        tool_calls=["format_decision_rationale"],
        duration_ms=duration_ms,
    )
    result: dict[str, Any] = {
        "decision_event": decision.model_dump(mode="json"),
        "trace_events": state.get("trace_events", []) + [trace],
    }
    return result


def operator_copilot(state: AXONAgentState) -> dict:
    """Advisory copilot — only writes copilot_explanation."""
    t0 = time.monotonic()
    llm_used = False
    explanation = ""

    if settings.axon_copilot_enabled:
        model = get_chat_model(settings)
        if isinstance(model, MockCopilotRunnable):
            explanation = model.invoke(dict(state))
        else:
            llm_used = True
            docs = get_rag_docs()
            policy_snippet = lookup_safety_policy("operator", docs)
            runbook_snippet = lookup_operational_runbook("simulation", docs)
            prompt = (
                f"Summarize this simulated rehab session for an operator. "
                f"Risk: {state['risk_level']}, action: {state['proposed_action']}, "
                f"confidence: {state['confidence']}. "
                f"Policy context: {policy_snippet[:200]}. "
                f"Runbook: {runbook_snippet[:200]}. "
                f"Use synthetic/operational language only. No medical claims."
            )
            try:
                response = model.invoke(prompt)
                explanation = response.content if hasattr(response, "content") else str(response)
            except Exception as exc:
                llm_used = False
                fallback = draft_operator_explanation(dict(state))
                explanation = f"[Copilot error] {exc}. Fallback: {fallback}"

    if not explanation:
        explanation = draft_operator_explanation(dict(state))

    duration_ms = (time.monotonic() - t0) * 1000
    rag_tools = (
        ["lookup_safety_policy", "lookup_operational_runbook"]
        if settings.axon_rag_enabled
        else []
    )
    trace = _make_trace(
        state,
        "operator_copilot",
        "completed",
        explanation[:300],
        llm_used=llm_used,
        duration_ms=duration_ms,
        tool_calls=rag_tools,
    )
    return {
        "copilot_explanation": explanation,
        "trace_events": state.get("trace_events", []) + [trace],
    }


def route_after_action(state: AXONAgentState) -> str:
    """Conditional routing: HITL branch ends graph early."""
    if state.get("requires_human_confirmation"):
        return "end_hitl"
    return "operator_copilot"
