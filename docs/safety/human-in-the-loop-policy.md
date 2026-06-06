# Human-in-the-Loop (HITL) Policy

AXON agents may recommend simulated operational actions but must not act as clinical authority.

## Core Rules

1. **High-risk or low-confidence actions require operator confirmation** before execution in simulation.
2. **Safety thresholds must be documented** in code and runbooks (Phase 3+).
3. **Agent recommendations must be traceable** via `DecisionEventV1` and `AgentTraceEventV1` with `trace_id`.
4. **LLM/copilot output is explanatory, not authoritative** — decisions flow through LangGraph state and safety policies.
5. **Future implementation must include audit logs** for safety decisions and operator responses.

## Risk Levels

| Risk Level | Example Actions | HITL Required |
|------------|-----------------|---------------|
| Low | Continue session, log anomaly | No (default) |
| Medium | Reduce robot velocity | Configurable |
| High | Pause rehab session | Yes |
| Critical | Emergency stop simulation | Yes + explicit operator ack |

## Confidence Thresholds (Future)

Thresholds will be defined in Phase 3 implementation. Until then:

- Document placeholder thresholds in agent configuration
- Never auto-execute high-risk actions without `requires_human_confirmation=true` in decision events

## Operator UI (Future)

Dashboard must present:

- Recommended action and rationale
- Related event IDs and trace link
- Confirm / reject controls with audit trail

## Audit Requirements (Future Phases)

- Timestamped operator decisions
- Agent trace correlation
- Immutable log export for Evidence Center

## Phase 0 Note

Policy is defined; HITL workflows are not implemented until Phase 3.
