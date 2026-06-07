# Operator Copilot Runbook (Phase 3)

## Purpose

The Operator Copilot explains simulated rehab session assessments. It is **advisory only** and cannot authorize critical actions.

## Modes

| Mode | Env | Behavior |
|------|-----|----------|
| Mock (default) | `AXON_LLM_MODE=mock` | Deterministic template output, no external calls |
| Real | `AXON_LLM_MODE=real` + provider key | LangChain provider summarizes evidence |

## Enable Real LLM (Portfolio Demo)

```bash
export AXON_LLM_MODE=real
export AXON_LLM_PROVIDER=openai   # or anthropic, google
export AXON_LLM_MODEL=gpt-4o-mini
export OPENAI_API_KEY=sk-...
docker compose --profile core --profile llm up --build
```

## What the Copilot May Do

- Summarize synthetic telemetry and operational simulation scores
- Retrieve local safety/runbook docs via keyword RAG
- Draft operator-facing rationale text

## What the Copilot May NOT Do

- Approve or reject HITL decisions
- Lower risk level or bypass human confirmation
- Change `recommended_action` after Safety Agent
- Invent missing telemetry
- Make medical claims

## Human-in-the-Loop

When `requires_human_confirmation=true`:

1. Decision stored in Redis pending keys
2. Dashboard shows Confirm / Reject buttons
3. Operator action writes updated DecisionEventV1 to stream
4. Pending entries expire after `AXON_HITL_EXPIRY_SECONDS` (default 120)

## Failure Injection

Use dashboard buttons or API to simulate degraded inputs. All scenarios auto-reset after 30s or via `/api/v1/failure-injection/reset`.
