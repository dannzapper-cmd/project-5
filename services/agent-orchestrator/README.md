# Agent Orchestrator

## Purpose

Coordinate stateful agent workflows using LangGraph with LangChain tools, RAG, retrievers, and model-call layer.

## Future Phase

Phase 3 — Agents + Safety

## Expected Inputs

- Fusion state and model scores
- Safety policies and HITL thresholds
- Operator context (simulated)

## Expected Outputs

- `DecisionEventV1` and `AgentTraceEventV1` events
- Human-in-the-loop confirmation requests

## Evidence to Collect

- LangGraph decision trace screenshot
- LangChain tool/RAG evidence
- HITL confirmation workflow screenshot

## Current Phase 0 Status

**Placeholder only.** No LangGraph or LangChain runtime implemented.
