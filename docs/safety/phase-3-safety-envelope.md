# Phase 3 Safety Envelope

## Language Requirements

Use: synthetic signal, simulated rehab session, operational simulation score, simulated risk, operator recommendation, requires human confirmation.

Do not use: diagnosis, patient treatment, clinical decision, medical-grade, real patient, doctor recommendation, therapeutic prescription.

## Safety Architecture (Phase 3)

1. **Deterministic Safety Agent** — priority-ordered rules, no LLM
2. **Advisory Operator Copilot** — mock default, optional real LLM
3. **Redis durable HITL** — pending decisions survive restarts
4. **Failure injection** — controlled degradation for demo/evidence
5. **LLM authority: advisory only** — structurally enforced in graph node return dicts

## Safety Agent Rule Priority

1. Corrupt inputs → ignore / quarantine
2. Critical risk → escalate simulated alert + HITL
3. High risk → pause simulation + HITL
4. Low confidence on elevated risk → hold for more data + HITL
5. Stale telemetry on elevated risk → request operator check + HITL
6. Stale telemetry on nominal/low → continue with warning
7. Default → continue session

## Copilot Constraints

The Operator Copilot node returns **only** `copilot_explanation`. It cannot modify `risk_level`, `proposed_action`, or `requires_human_confirmation`.
