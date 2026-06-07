"""Deterministic Safety Agent rules (Phase 3)."""

from __future__ import annotations

import os

from apps.api.app.agents.state import AXONAgentState
from apps.api.app.langchain.rag import get_rag_docs
from apps.api.app.langchain.tools import format_decision_rationale, lookup_safety_policy

HIGH_RISK_THRESHOLD = float(os.getenv("AXON_SAFETY_HIGH_RISK_THRESHOLD", "0.75"))
LOW_CONF_THRESHOLD = float(os.getenv("AXON_SAFETY_LOW_CONFIDENCE_THRESHOLD", "0.55"))


def apply_safety_rules(state: AXONAgentState) -> dict:
    """Apply mandatory safety rules in exact priority order."""
    # Rule 1: corrupt inputs — quarantine
    if state["corrupt_inputs"]:
        return {
            "proposed_action": "ignore_corrupt_event",
            "requires_human_confirmation": False,
            "risk_level": state["risk_level"],
            "safety_verdict": {"rule": "corrupt_quarantine"},
            "safety_constraints": ["corrupt_event_quarantined"],
        }

    # Rule 2: critical risk
    if state["risk_level"] == "critical":
        return {
            "proposed_action": "escalate_simulated_alert",
            "requires_human_confirmation": True,
            "risk_level": state["risk_level"],
            "safety_verdict": {"rule": "critical_risk"},
            "safety_constraints": ["critical_simulated_risk_requires_operator"],
        }

    # Rule 3: high risk
    if state["risk_level"] == "high":
        return {
            "proposed_action": "pause_simulation",
            "requires_human_confirmation": True,
            "risk_level": state["risk_level"],
            "safety_verdict": {"rule": "high_risk"},
            "safety_constraints": ["high_simulated_risk_requires_confirmation"],
        }

    # Rule 4: low confidence on non-nominal risk
    if state["confidence"] < LOW_CONF_THRESHOLD and state["risk_level"] not in ("nominal", "low"):
        return {
            "proposed_action": "hold_for_more_data",
            "requires_human_confirmation": True,
            "risk_level": state["risk_level"],
            "safety_verdict": {"rule": "low_confidence_elevated_risk"},
            "safety_constraints": ["low_confidence_hold"],
        }

    # Rule 5: stale inputs on elevated risk
    if state["stale_inputs"] and state["risk_level"] in ("medium", "high", "critical"):
        return {
            "proposed_action": "request_operator_check",
            "requires_human_confirmation": True,
            "risk_level": state["risk_level"],
            "safety_verdict": {"rule": "stale_elevated_risk"},
            "safety_constraints": ["stale_telemetry_elevated_risk"],
        }

    # Rule 6: stale inputs on nominal/low — continue with warning
    if state["stale_inputs"] and state["risk_level"] in ("nominal", "low"):
        return {
            "proposed_action": "continue_session",
            "requires_human_confirmation": False,
            "risk_level": state["risk_level"],
            "safety_verdict": {"rule": "stale_nominal_continue"},
            "safety_constraints": ["stale_telemetry_warning"],
        }

    # Rule 7: nominal — continue
    return {
        "proposed_action": state.get("proposed_action", "continue_session"),
        "requires_human_confirmation": False,
        "risk_level": state["risk_level"],
        "safety_verdict": {"rule": "nominal_continue"},
        "safety_constraints": [],
    }


def build_safety_rationale(state: AXONAgentState) -> str:
    """Build rationale string with optional safety policy citation."""
    base = format_decision_rationale(dict(state))
    docs = get_rag_docs()
    policy = lookup_safety_policy("human-in-the-loop", docs)
    if policy and "No matching" not in policy:
        return f"{base} Safety policy ref: {policy[:200]}"
    return base
