"""LangChain layer for Phase 3 agents."""

from apps.api.app.langchain.provider import MockCopilotRunnable, get_chat_model
from apps.api.app.langchain.rag import get_rag_docs, load_rag_documents
from apps.api.app.langchain.tools import (
    draft_operator_explanation,
    format_decision_rationale,
    get_latest_model_scores,
    get_recent_telemetry_summary,
    lookup_operational_runbook,
    lookup_safety_policy,
)

__all__ = [
    "MockCopilotRunnable",
    "get_chat_model",
    "get_rag_docs",
    "load_rag_documents",
    "draft_operator_explanation",
    "format_decision_rationale",
    "get_latest_model_scores",
    "get_recent_telemetry_summary",
    "lookup_operational_runbook",
    "lookup_safety_policy",
]
