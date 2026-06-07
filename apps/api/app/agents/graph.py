"""LangGraph StateGraph compilation for Phase 3."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from apps.api.app.agents.nodes import (
    action_recommendation_agent,
    operator_copilot,
    perception_agent,
    route_after_action,
    safety_agent,
    triage_agent,
)
from apps.api.app.agents.state import AXONAgentState


def build_agent_graph() -> StateGraph:
    """Build and return uncompiled StateGraph with mandatory topology."""
    graph = StateGraph(AXONAgentState)

    graph.add_node("perception_agent", perception_agent)
    graph.add_node("triage_agent", triage_agent)
    graph.add_node("safety_agent", safety_agent)
    graph.add_node("action_recommendation_agent", action_recommendation_agent)
    graph.add_node("operator_copilot", operator_copilot)

    graph.set_entry_point("perception_agent")
    graph.add_edge("perception_agent", "triage_agent")
    graph.add_edge("triage_agent", "safety_agent")
    graph.add_edge("safety_agent", "action_recommendation_agent")
    graph.add_conditional_edges(
        "action_recommendation_agent",
        route_after_action,
        {
            "end_hitl": END,
            "operator_copilot": "operator_copilot",
        },
    )
    graph.add_edge("operator_copilot", END)

    return graph


def get_compiled_graph():
    """Return compiled agent graph."""
    return build_agent_graph().compile()
