"""Pure LangChain-style tools for Phase 3 agent graph (no side effects)."""

from __future__ import annotations


def get_recent_telemetry_summary(snapshot: dict) -> str:
    """Summarize pre-loaded telemetry snapshot."""
    if not snapshot:
        return "No synthetic telemetry available in snapshot."
    lines = []
    for signal, data in snapshot.items():
        if isinstance(data, dict):
            quality = data.get("quality", "—")
            ts = data.get("timestamp", "—")
            lines.append(f"{signal}: quality={quality}, ts={ts}")
        else:
            lines.append(f"{signal}: present")
    return "; ".join(lines) if lines else "Empty telemetry snapshot."


def get_latest_model_scores(snapshot: dict) -> str:
    """Summarize pre-loaded model score snapshot."""
    if not snapshot:
        return "No operational simulation scores in snapshot."
    lines = []
    for model, data in snapshot.items():
        if isinstance(data, dict):
            score = data.get("score", "—")
            conf = data.get("confidence", "—")
            label = data.get("output_label", "—")
            lines.append(f"{model}: score={score}, confidence={conf}, label={label}")
        else:
            lines.append(f"{model}: present")
    return "; ".join(lines) if lines else "Empty model score snapshot."


def lookup_safety_policy(query: str, docs: list) -> str:
    """Keyword-match safety policy docs."""
    query_lower = query.lower()
    matches = [d.page_content for d in docs if query_lower in d.page_content.lower()]
    return matches[0][:500] if matches else "No matching safety policy found."


def lookup_operational_runbook(query: str, docs: list) -> str:
    """Keyword-match operational runbook docs."""
    query_lower = query.lower()
    matches = [d.page_content for d in docs if query_lower in d.page_content.lower()]
    return matches[0][:500] if matches else "No matching operational runbook found."


def draft_operator_explanation(state_snapshot: dict) -> str:
    """Draft operator-facing explanation from state snapshot."""
    return (
        f"Simulated rehab session assessment: risk={state_snapshot.get('risk_level', 'unknown')}, "
        f"action={state_snapshot.get('proposed_action', 'unknown')}, "
        f"confidence={state_snapshot.get('confidence', 0):.2f}. "
        f"Synthetic signal inputs only. Requires human confirmation: "
        f"{state_snapshot.get('requires_human_confirmation', False)}."
    )


def format_decision_rationale(state_snapshot: dict) -> str:
    """Format decision rationale from state snapshot."""
    parts = [
        f"Operational simulation score confidence: {state_snapshot.get('confidence', 0):.2f}.",
        f"Simulated risk level: {state_snapshot.get('risk_level', 'unknown')}.",
        f"Recommended operator action: {state_snapshot.get('proposed_action', 'unknown')}.",
    ]
    if state_snapshot.get("stale_inputs"):
        parts.append("Warning: stale synthetic telemetry detected.")
    if state_snapshot.get("corrupt_inputs"):
        parts.append("Corrupt synthetic event quarantined.")
    if state_snapshot.get("missing_signals"):
        parts.append(f"Missing signals: {', '.join(state_snapshot['missing_signals'])}.")
    return " ".join(parts)
