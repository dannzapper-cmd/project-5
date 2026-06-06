# AXON Architecture

AXON is an event-driven Edge AI + IoT + robotics software system for **Simulated Rehab Robot Ops**.

## Design Principles

1. **Contracts first** — Pydantic event schemas and topic taxonomy before runtime wiring
2. **Profile-based activation** — Docker Compose profiles stage heavy dependencies
3. **Evidence-driven** — every major capability produces demonstrable artifacts
4. **Local-first** — modular development without mandatory cloud or hardware
5. **Safety boundaries** — synthetic signals, human-in-the-loop for high-risk actions

## Documents

| Document | Description |
|----------|-------------|
| [system-context.md](system-context.md) | C4-style system context diagram |
| [event-flow.md](event-flow.md) | End-to-end event flow |
| [profiles.md](profiles.md) | Docker Compose profile strategy |

## Phase 0 Status

Architecture documentation and diagrams describe the **target system**. Runtime services are placeholders except:

- FastAPI health endpoint
- Pydantic event schemas
- Docker Compose skeleton (core profile)

See [ROADMAP.md](../../ROADMAP.md) for implementation timeline.
