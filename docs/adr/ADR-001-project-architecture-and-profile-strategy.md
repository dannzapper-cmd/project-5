# ADR-001: Project Architecture and Profile Strategy

- **Status:** Accepted
- **Date:** 2026-06-05
- **Deciders:** AXON project owners

## Context

AXON is a portfolio-grade intelligent systems project spanning Edge AI, IoT telemetry, agent orchestration, MLOps, robotics, and observability. Running every component simultaneously would:

- Increase local development friction
- Encourage fake "everything works" demos
- Obscure phase boundaries and evidence collection
- Make cost and hardware trade-offs invisible

The fixed scenario is **Simulated Rehab Robot Ops** with synthetic biomedical-inspired signals only. The system must remain modular, evidence-driven, and honest about what is implemented.

## Decision

1. **Event-driven architecture** with Pydantic contracts as the integration boundary across MQTT, Redis Streams, WebSockets, and future ROS2 topics.
2. **Phase-gated implementation** documented in `ROADMAP.md` — Phase 0 delivers contracts and skeleton only.
3. **Docker Compose profiles** (`core`, `obs`, `learning`, `ros2`, `ros2-nav-slam`, `sim`, `llm`, `full`) control which services activate.
4. **Evidence Center** checklist tracks demonstrable proof per phase.
5. **Local-first default** with optional cloud/VM and hardware paths activated on demand.
6. **Contracts before runtime** — schemas, topic taxonomy, ADRs, and safety policies precede telemetry and ML implementation.

## Consequences

### Positive

- Contributors can work on isolated phases without heavyweight dependencies
- Demo commands remain reproducible and scoped
- Architecture trade-offs are documented and reviewable
- Future PRs have clear boundaries and acceptance criteria

### Negative

- Initial clone does not show a "flashy" full system — intentional honesty
- Profile matrix adds operational complexity — mitigated by Makefile targets and docs
- Cross-service integration deferred until explicit phases — requires discipline

## Alternatives Considered

| Alternative | Why Not Chosen |
|-------------|----------------|
| Monolithic always-on stack | Violates local-first and cost-awareness principles |
| Kubernetes as mandatory | Overkill for portfolio/local development |
| Kafka as core bus | Redis Streams sufficient for local-first replay/buffering |
| Implement features before contracts | Produces untestable integrations and false demos |
| Skip Evidence Center | Removes senior-leaning proof of capability |

## Why Profile-Based Execution Matters

Profiles encode **staged activation**:

- `core` supports daily API and schema work
- `obs`, `learning`, `ros2*` activate only when those roadmap phases begin
- `full` is reserved for late integration, not default dev

This supports modular local-first development, optional cloud/VM execution, and documented trade-offs without requiring all hardware or cloud services.

## Why Phase 0 Starts with Contracts

Phase 0 establishes the **product contract**:

- Event schemas and topic taxonomy
- Safety and biomedical boundaries
- Architecture diagrams and ADRs
- Compose profiles and health endpoint

Runtime capabilities (telemetry spine, inference, agents) build on stable contracts in subsequent PRs.

## Why Evidence-Driven Implementation

Every major technology must eventually produce visible evidence: streams, traces, metrics, screenshots, benchmarks, model cards, or reproducible demo commands. This prevents decorative documentation and ensures portfolio credibility.
