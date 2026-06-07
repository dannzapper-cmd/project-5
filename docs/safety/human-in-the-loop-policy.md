# Human-in-the-Loop (HITL) Policy

AXON agents may recommend simulated operational actions but must not act as clinical authority.

## Core Rules

1. **High-risk or low-confidence actions require operator confirmation** before execution in simulation.
2. **Safety thresholds are documented** in `.env.example` and `apps/api/app/agents/safety.py`.
3. **Agent recommendations are traceable** via `DecisionEventV1` and `AgentTraceEventV1` with `trace_id`.
4. **LLM/copilot output is explanatory, not authoritative** — Safety Agent verdict fields cannot be modified by copilot.
5. **Pending decisions stored in Redis** (`axon:v1:pending_decisions`) with TTL expiry.

## Risk Levels

| Risk Level | Example Actions | HITL Required |
|------------|-----------------|---------------|
| Nominal / Low | Continue simulated session | No (unless stale warning) |
| Medium | Reduce intensity | Yes if low confidence |
| High | Pause simulation | Yes |
| Critical | Escalate simulated alert | Yes |

## Confidence Thresholds (Phase 3)

| Variable | Default | Effect |
|----------|---------|--------|
| `AXON_SAFETY_LOW_CONFIDENCE_THRESHOLD` | 0.55 | Hold / HITL on elevated risk |
| `AXON_SAFETY_HIGH_RISK_THRESHOLD` | 0.75 | Used in triage scoring context |
| `AXON_HITL_EXPIRY_SECONDS` | 120 | Pending decisions expire |

## Operator UI (Phase 3)

Dashboard presents:

- Recommended action and rationale (synthetic / operational language)
- Evidence refs and contributing signals
- Confirm / reject controls with optional operator note
- Decision timeline with status changes

## Audit Trail

- Confirm/reject writes updated `DecisionEventV1` to Redis decisions stream
- `human_response` object records operator_id, response, note, timestamp
- Agent traces retained in `axon:v1:stream:agent_traces`
