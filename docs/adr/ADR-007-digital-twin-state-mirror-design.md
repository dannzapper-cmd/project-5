# ADR-007: Digital Twin State Mirror Design (Phase 5)

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** AXON project owners
- **Also referenced as:** ADR-005 (Phase 5 addendum) — Digital Twin State Mirror Design

## Context

AXON Phases 1–4 deliver live synthetic telemetry, ONNX inference, agent orchestration, HITL safety, and MLOps. Phase 5 requires a **verifiable digital twin** that mirrors operational state without pretending to be a physics simulator or clinical system.

Heavy simulation stacks (Gazebo, Isaac Sim, Omniverse) would violate the profile-based, lightweight default install strategy and distract from the portfolio goal: **honest edge/robotics command visibility**.

## Decision

1. **State mirror, not physics engine** — `DigitalTwinStateV1` is derived deterministically from existing Redis Streams, agent in-memory state, and safety envelopes. No parallel telemetry pipeline.
2. **Versioned Pydantic contract** — `DigitalTwinStateV1` and sub-schemas live in `apps/api/app/schemas/twin.py` with `schema_version: v1`.
3. **Twin service inside API** — `apps/api/app/twin/service.py` consumes:
   - Redis: `axon:v1:stream:sensors:*`, `robot_state`, `model_scores`, `agent_traces`, `decisions`, `alerts`
   - In-process agent/safety snapshots
   - Emits: WebSocket `twin` channel (`/ws/v1/twin`), Redis `axon:v1:stream:fusion`
4. **Configurable timing contracts** — `TWIN_BROADCAST_HZ`, `SENSOR_STALE_TTL_SECONDS`, `SENSOR_DROPOUT_TTL_SECONDS` drive stale/dropout transitions and auto-degraded robot mode.
5. **Lightweight dashboard mirror** — SVG/canvas 2D visualization in `apps/dashboard/` (no Three.js) reacts to live WebSocket twin state and replay scenarios.
6. **Safe command endpoint** — `POST /api/v1/twin/command` with HITL/safety boundaries; no medical claims.

## Trade-offs

| Choice | Benefit | Cost |
|--------|---------|------|
| State mirror vs Gazebo | Fast, reproducible, CI-friendly | No collision/physics fidelity |
| API-embedded twin vs separate service | Reuses Redis/agent integration | API process owns broadcast loop |
| SVG vs 3D | Zero new frontend deps | Less immersive than full 3D twin |

## Consequences

- Digital twin is **operationally honest** — it shows what AXON knows from telemetry/agents, not simulated physics.
- Staleness and dropout are visible within configured TTL windows.
- Phase 5.5 can add Nav2/SLAM poses without replacing this contract.
- Evidence screenshots (normal, warning, degraded, HITL) are required for acceptance.

## Out of scope (Phase 5)

- Gazebo / Isaac / Omniverse
- Real patient data or clinical claims
- Nav2, SLAM, navigation stack
