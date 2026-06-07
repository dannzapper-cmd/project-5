"""LangChain model provider factory with lazy real-provider imports."""

from __future__ import annotations

from typing import Any, Protocol

from apps.api.app.core.config import Settings


class CopilotRunnable(Protocol):
    """Minimal runnable interface for operator copilot."""

    def invoke(self, state: dict) -> str: ...


class MockCopilotRunnable:
    """Deterministic offline copilot — no external calls."""

    def invoke(self, state: dict) -> str:
        missing = state.get("missing_signals") or []
        signals = ", ".join(missing) if missing else "all_present"
        confirm = "required" if state["requires_human_confirmation"] else "not required"
        return (
            f"[AXON MOCK COPILOT v1] Simulated session assessment complete. "
            f"Risk level: {state['risk_level']}. "
            f"Recommended action: {state['proposed_action']}. "
            f"Confidence: {state['confidence']:.2f}. "
            f"Contributing signals: {signals}. "
            f"Stale inputs: {state['stale_inputs']}. Corrupt inputs: {state['corrupt_inputs']}. "
            f"This is a synthetic signal simulation. No clinical inference has been performed. "
            f"Operator confirmation {confirm}."
        )


def get_chat_model(settings: Settings) -> CopilotRunnable | Any:
    """Return mock or real LangChain chat model based on settings."""
    if settings.axon_llm_mode == "mock" or not settings.axon_llm_mode:
        return MockCopilotRunnable()

    if settings.axon_llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when AXON_LLM_PROVIDER=openai.")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "langchain-openai not installed. "
                "Set AXON_LLM_MODE=mock or install langchain-openai."
            ) from exc
        return ChatOpenAI(
            model=settings.axon_llm_model,
            api_key=settings.openai_api_key,
            timeout=settings.axon_llm_timeout_seconds,
            max_tokens=settings.axon_llm_max_tokens,
        )

    if settings.axon_llm_provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise RuntimeError("langchain-anthropic not installed.") from exc
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY required.")
        return ChatAnthropic(
            model=settings.axon_llm_model,
            api_key=settings.anthropic_api_key,
        )

    if settings.axon_llm_provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise RuntimeError("langchain-google-genai not installed.") from exc
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY required.")
        return ChatGoogleGenerativeAI(
            model=settings.axon_llm_model,
            google_api_key=settings.google_api_key,
        )

    raise RuntimeError(f"Unknown AXON_LLM_PROVIDER: {settings.axon_llm_provider}")
