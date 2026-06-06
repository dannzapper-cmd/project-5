# ADR-002: Redis Streams over Kafka for Local-First Replay and Buffering

- **Status:** Proposed
- **Date:** 2026-06-05

## Context

AXON requires a durable buffer between ingest and downstream consumers (inference, fusion, agents) with replay support for demos and failure injection. The system prioritizes local-first development and modular profiles.

## Decision to Evaluate

Adopt **Redis Streams** as the primary event buffer and replay substrate instead of Apache Kafka.

## Options to Compare

| Option | Pros | Cons |
|--------|------|------|
| Redis Streams | Lightweight, local-friendly, consumer groups, replay via stream IDs | Less ecosystem than Kafka at very large scale |
| Apache Kafka | High throughput, mature ecosystem | Heavier ops burden for local dev |
| In-memory only | Simplest | No replay, no durability |

## Evidence Needed

- Consumer group lag under simulated sensor load (Phase 1)
- Replay determinism with preserved `trace_id` (Phase 1)
- Memory/CPU profile under `core` profile (Phase 7)

## Future Phase

Phase 1 — Telemetry Spine (initial Redis Streams wiring)
