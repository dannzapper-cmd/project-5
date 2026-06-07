# ADR-004: LangGraph + LangChain Safety Copilot

## Status

Accepted (Phase 3)

## Context

AXON Phase 3 requires stateful agent orchestration over synthetic telemetry and operational simulation scores. A simple LLM call chain cannot:

- Enforce deterministic safety rules before recommendations
- Route high-risk decisions to human-in-the-loop without LLM override
- Emit traceable AgentTraceEventV1 per step and DecisionEventV1 per cycle
- Run offline in core Docker profile without API keys

## Decision

1. **LangGraph `StateGraph`** with `AXONAgentState` TypedDict for orchestration
2. **LangChain** for tools, keyword RAG, and provider abstraction (mock default)
3. **Redis-based durable HITL** — pending decisions stored in Redis keys (`axon:v1:pending_decisions`, `axon:v1:pending_decision:{id}`) with optional in-process cache
4. **Conditional edge** after action_recommendation_agent: HITL branch ends graph before copilot
5. **Safety Agent** applies deterministic rules only — no LLM inside safety node
6. **Operator Copilot** is advisory only; structurally returns only `copilot_explanation`

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| CrewAI | No explicit conditional edges; weaker HITL control |
| Native LangGraph checkpointer interrupts | Async checkpointer complexity with FastAPI lifespan |
| Pure Python state machine | No graph visualization; weaker tool abstraction |
| Module-level dict only for HITL | Not durable across restarts; Redis is source of truth |

## Consequences

- LLM cannot override Safety Agent verdict fields (enforced by node return dicts)
- HITL survives process restarts via Redis pending keys
- Mock mode requires zero external LLM dependencies
- Real LLM mode enabled via env vars / `llm` profile; core profile never requires keys
- Failure injection modifies agent state building, not live telemetry pipeline
