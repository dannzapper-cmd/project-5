# ADR-004: LangGraph and LangChain Agent Stack

- **Status:** Proposed
- **Date:** 2026-06-05

## Context

AXON requires stateful agent orchestration for safety decisions, human-in-the-loop workflows, and traceable recommendations in simulated rehab operations. The project must not collapse into a generic chatbot.

## Decision to Evaluate

- **LangGraph** as the main stateful agent orchestration runtime
- **LangChain** as the required tools, RAG, retriever, research/model-call, and connector layer

AutoGen and CrewAI are explicitly **not** the main agent framework.

## Options to Compare

| Option | Pros | Cons |
|--------|------|------|
| LangGraph + LangChain | Stateful graphs, tool ecosystem, traceability | Learning curve, dependency weight |
| Custom state machine | Minimal deps | Reinvents orchestration patterns |
| AutoGen / CrewAI | Multi-agent hype | Not selected as main framework per project mandate |

## Evidence Needed

- LangGraph decision trace screenshots (Phase 3)
- LangChain tool/RAG invocation logs (Phase 3)
- HITL confirmation workflow demo (Phase 3)

## Future Phase

Phase 3 — Agents + Safety
