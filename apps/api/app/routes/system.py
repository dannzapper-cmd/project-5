"""System / capability introspection routes for the demo cockpit.

These endpoints expose honest, non-secret runtime metadata so the dashboard can
prove it is talking to a live backend and can explain optional/profile-gated
capabilities. No secrets are returned (only whether a key is configured), and
the copilot explanation is the deterministic offline mock unless a real LLM
provider is explicitly configured by the operator.

Synthetic simulation only. Not a medical device. No clinical claims.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from apps.api.app.agents.service import get_current_decision, get_safety_status
from apps.api.app.core.config import settings
from apps.api.app.langchain.provider import MockCopilotRunnable

router = APIRouter(prefix="/api/v1/system", tags=["system"])

COPILOT_AUTHORITY = "advisory_only"
SAFETY_NOTICE = (
    "Synthetic simulation only. Not a medical device. No clinical inference. "
    "Operator copilot is advisory only and cannot authorize critical actions."
)


@router.get("/info")
def system_info(request: Request) -> dict:
    """Non-secret runtime metadata for the backend-proof and copilot panels."""
    real_provider = settings.axon_llm_provider not in ("mock", "")
    provider_key_map = {
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "google": bool(settings.google_api_key),
    }
    real_llm_configured = real_provider and provider_key_map.get(
        settings.axon_llm_provider, False
    )
    return {
        "service": settings.service_name,
        "version": settings.version,
        "env": settings.axon_env,
        "timestamp": datetime.now(UTC).isoformat(),
        "trace_id": getattr(request.state, "trace_id", None),
        "llm": {
            "mode": settings.axon_llm_mode,
            "provider": settings.axon_llm_provider,
            "model": settings.axon_llm_model,
            "copilot_enabled": settings.axon_copilot_enabled,
            "rag_enabled": settings.axon_rag_enabled,
            "authority": COPILOT_AUTHORITY,
            "real_llm_configured": real_llm_configured,
            "activation": (
                "Real LLM is optional. Set AXON_LLM_MODE=real, AXON_LLM_PROVIDER, "
                "and the matching API key on the api service, then restart core."
            ),
        },
        "safety_notice": SAFETY_NOTICE,
    }


class CopilotExplainRequest(BaseModel):
    operator_note: str = ""


@router.post("/copilot/explain")
def copilot_explain(body: CopilotExplainRequest, request: Request) -> dict:
    """Generate a deterministic advisory copilot explanation for the current state.

    Uses the current safety status and the latest decision (when present) as the
    grounding state. In mock mode this is fully offline and deterministic; it
    never authorizes actions and performs no clinical inference.
    """
    safety = get_safety_status()
    decision = get_current_decision() or {}
    default_risk = "high" if safety.get("high_risk") else "nominal"
    state = {
        "risk_level": decision.get("risk_level") or default_risk,
        "proposed_action": decision.get("recommended_action") or "continue_session",
        "confidence": float(decision.get("confidence") or 0.85),
        "requires_human_confirmation": bool(decision.get("requires_human_confirmation")),
        "missing_signals": safety.get("missing_signals") or [],
        "stale_inputs": bool(safety.get("stale_telemetry")),
        "corrupt_inputs": "corrupt_event" in (safety.get("active_injections") or []),
    }
    explanation = MockCopilotRunnable().invoke(state)
    trace_id = getattr(request.state, "trace_id", None) or "copilot-mock"
    return {
        "mode": settings.axon_llm_mode,
        "provider": settings.axon_llm_provider,
        "authority": COPILOT_AUTHORITY,
        "explanation": explanation,
        "grounded_on": {
            "decision_id": decision.get("decision_id"),
            "risk_level": state["risk_level"],
            "requires_human_confirmation": state["requires_human_confirmation"],
        },
        "operator_note": body.operator_note,
        "trace_id": trace_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "safety_notice": SAFETY_NOTICE,
    }
