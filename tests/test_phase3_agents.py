"""Phase 3 agents + safety tests (offline, no real LLM/Redis)."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta

import pytest
from apps.api.app.agents import service as agent_service
from apps.api.app.agents.failure_injection import activate_injection, reset_injections
from apps.api.app.agents.graph import get_compiled_graph
from apps.api.app.agents.hitl import (
    cache_pending,
    get_cached_pending,
    run_expiry_check,
)
from apps.api.app.agents.safety import apply_safety_rules
from apps.api.app.agents.service import build_initial_state
from apps.api.app.core.config import Settings
from apps.api.app.langchain.provider import MockCopilotRunnable, get_chat_model
from apps.api.app.schemas.events import DecisionEventV1
from apps.api.app.telemetry.websocket_manager import ws_manager


def build_nominal_test_state():
    now = datetime.now(UTC).isoformat()
    return build_initial_state(
        "session-synthetic-001",
        "trace-test-nominal",
        {
            "emg": {"timestamp": now, "quality": 0.95, "values": [0.1]},
            "imu": {"timestamp": now, "quality": 0.92, "values": [0.0]},
            "ecg_like": {"timestamp": now, "quality": 0.9, "values": [0.5]},
            "spo2_proxy": {"timestamp": now, "quality": 0.88, "values": [0.98]},
        },
        {
            "emg_anomaly": {
                "score": 0.1,
                "confidence": 0.9,
                "output_label": "normal",
                "timestamp": now,
            },
        },
    )


def build_high_risk_state():
    now = datetime.now(UTC).isoformat()
    state = build_nominal_test_state()
    state["model_score_snapshot"] = {
        "emg_anomaly": {
            "score": 0.95,
            "confidence": 0.85,
            "output_label": "elevated_activity",
            "timestamp": now,
        },
    }
    return state


def build_pending_decision() -> DecisionEventV1:
    now = datetime.now(UTC) - timedelta(seconds=5)
    return DecisionEventV1(
        trace_id="trace-hitl",
        source="axon-api",
        session_id="session-synthetic-001",
        input_window_start=now,
        input_window_end=now,
        risk_level="high",
        confidence=0.6,
        recommended_action="pause_simulation",
        requires_human_confirmation=True,
        status="pending_human_confirmation",
        rationale="Simulated high risk requires operator confirmation.",
        timestamp=now,
    )


@pytest.fixture
def compiled_graph():
    return get_compiled_graph()


# --- Schema-adjacent safety tests ---


def test_high_risk_requires_human_confirmation():
    state = build_nominal_test_state()
    state["risk_level"] = "high"
    result = apply_safety_rules(state)
    assert result["requires_human_confirmation"] is True
    assert result["proposed_action"] == "pause_simulation"


def test_low_confidence_requires_hold():
    state = build_nominal_test_state()
    state["risk_level"] = "medium"
    state["confidence"] = 0.3
    result = apply_safety_rules(state)
    assert result["requires_human_confirmation"] is True
    assert result["proposed_action"] == "hold_for_more_data"


def test_stale_elevated_risk_cannot_continue_confidently():
    state = build_nominal_test_state()
    state["risk_level"] = "medium"
    state["stale_inputs"] = True
    state["confidence"] = 0.9
    result = apply_safety_rules(state)
    assert result["proposed_action"] == "request_operator_check"
    assert result["requires_human_confirmation"] is True


def test_corrupt_event_ignored():
    state = build_nominal_test_state()
    state["corrupt_inputs"] = True
    result = apply_safety_rules(state)
    assert result["proposed_action"] == "ignore_corrupt_event"
    assert result["requires_human_confirmation"] is False


def test_stale_nominal_continues_with_warning():
    state = build_nominal_test_state()
    state["stale_inputs"] = True
    state["risk_level"] = "nominal"
    result = apply_safety_rules(state)
    assert result["proposed_action"] == "continue_session"
    assert result["requires_human_confirmation"] is False


# --- LangChain provider tests ---


def test_mock_provider_deterministic():
    state = build_nominal_test_state()
    out1 = MockCopilotRunnable().invoke(state)
    out2 = MockCopilotRunnable().invoke(state)
    assert out1 == out2
    assert "[AXON MOCK COPILOT v1]" in out1
    assert "No clinical inference has been performed" in out1


def test_missing_key_real_provider_raises():
    settings = Settings(
        axon_llm_mode="real",
        axon_llm_provider="openai",
        openai_api_key="",
    )
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_chat_model(settings)


def test_mock_mode_default_no_provider_import():
    settings = Settings()
    model = get_chat_model(settings)
    assert isinstance(model, MockCopilotRunnable)


# --- LangGraph tests ---


def test_graph_nominal_continue(compiled_graph):
    state = build_nominal_test_state()
    result = compiled_graph.invoke(state)
    assert result["decision_event"] is not None
    assert result["decision_event"]["recommended_action"] == "continue_session"
    assert result["risk_level"] in ("nominal", "low")
    assert set(result["decision_event"]["contributing_signals"]) == {
        "emg",
        "ecg_like",
        "imu",
        "spo2_proxy",
    }


def test_contributing_signals_excludes_missing(compiled_graph):
    reset_injections()
    activate_injection("sensor_dropout")
    state = build_nominal_test_state()
    result = compiled_graph.invoke(state)
    contributing = result["decision_event"]["contributing_signals"]
    missing = result["missing_signals"]
    assert not set(contributing) & set(missing)
    assert len(contributing) < 4
    reset_injections()


def test_llm_used_false_in_mock_mode(compiled_graph):
    state = build_nominal_test_state()
    result = compiled_graph.invoke(state)
    assert result["decision_event"]["llm_used"] is False
    copilot_traces = [
        t for t in result.get("trace_events", []) if t.get("agent_name") == "operator_copilot"
    ]
    assert copilot_traces
    assert copilot_traces[0]["llm_used"] is False


def test_graph_low_confidence_hitl(compiled_graph):
    reset_injections()
    activate_injection("model_low_confidence")
    state = build_nominal_test_state()
    result = compiled_graph.invoke(state)
    assert result["requires_human_confirmation"] is True
    assert result["decision_event"]["status"] == "pending_human_confirmation"
    reset_injections()


def test_graph_sensor_dropout_degraded(compiled_graph):
    reset_injections()
    activate_injection("sensor_dropout")
    state = build_nominal_test_state()
    result = compiled_graph.invoke(state)
    assert len(result["missing_signals"]) > 0 or result["confidence"] < 0.85
    reset_injections()


def test_graph_high_risk_pending_hitl(compiled_graph):
    state = build_high_risk_state()
    result = compiled_graph.invoke(state)
    assert result["requires_human_confirmation"] is True
    assert result["decision_event"]["status"] == "pending_human_confirmation"


def test_graph_mock_completes_within_2000ms(compiled_graph):
    state = build_nominal_test_state()
    t0 = time.monotonic()
    result = compiled_graph.invoke(state)
    elapsed_ms = (time.monotonic() - t0) * 1000
    assert elapsed_ms < 2000
    assert result["decision_event"] is not None


def test_copilot_cannot_modify_safety_verdict(compiled_graph):
    state = build_high_risk_state()
    result = compiled_graph.invoke(state)
    assert result["risk_level"] == "high"
    assert result["requires_human_confirmation"] is True
    if result.get("copilot_explanation"):
        assert "[AXON MOCK COPILOT" in result["copilot_explanation"]


# --- Agent loop / HITL tests ---


def test_concurrent_graph_execution_is_skipped(caplog):
    agent_service._graph_running = True
    asyncio.run(agent_service.agent_loop_tick(None, ws_manager))
    assert "agent_loop_skipped" in caplog.text
    agent_service._graph_running = False


def test_pending_decision_expires_after_ttl(monkeypatch):
    monkeypatch.setenv("AXON_HITL_EXPIRY_SECONDS", "1")
    decision = build_pending_decision()
    decision.timestamp = datetime.now(UTC) - timedelta(seconds=3)
    cache_pending(decision)
    time.sleep(0.1)
    asyncio.run(run_expiry_check(None, expiry_seconds=1))
    assert decision.decision_id not in get_cached_pending()


def test_failure_injection_auto_reset():
    reset_injections()
    activate_injection("stale_telemetry")
    from apps.api.app.agents import failure_injection

    failure_injection._active_injections["stale_telemetry"] = time.time() - 100
    failure_injection.evict_expired_injections()
    assert "stale_telemetry" not in failure_injection.active_scenarios()
