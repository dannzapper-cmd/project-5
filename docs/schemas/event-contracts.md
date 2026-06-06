# Event Contracts

Canonical event models live in `apps/api/app/schemas/events.py`.

## Shared Fields

All v1 events include:

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `"v1"` | Contract version |
| `event_id` | string (UUID) | Unique event identifier |
| `timestamp` | datetime (UTC) | Event creation time |
| `trace_id` | string | Correlation ID across pipeline |
| `source` | string | Publishing component name |

## Event Types (v1)

| Model | Purpose |
|-------|---------|
| `SensorEventV1` | Synthetic sensor telemetry |
| `DecisionEventV1` | Safety/operational decisions |
| `ModelScoreEventV1` | Edge inference output |
| `AgentTraceEventV1` | LangGraph step traces |
| `HealthEventV1` | Component health signals |

## Versioning Rules

1. **Additive changes** (optional fields) stay within `v1`
2. **Breaking changes** require `v2` models and dual-validation period
3. **Schema version** is explicit in every payload — never inferred from topic alone
4. Topic taxonomy version (`axon/v1/...`) aligns with but is independent from payload `schema_version`

## Trace ID Propagation

- Required on every event
- Must flow MQTT → Redis → inference → fusion → agents → WebSocket
- See [topic-taxonomy.md](topic-taxonomy.md) for fork rules

## Validation Before Inference

Events are validated at the API gateway **before** enqueue and inference:

1. Pydantic structural validation
2. Bound checks (`confidence`, `quality` ∈ [0, 1]; `latency_ms` ≥ 0)
3. Non-empty string and value constraints

**Rationale:** corrupt payloads must not silently enter ML pipelines or agent context.

## Missing and Corrupt Data

- Do **not** silently impute missing sensor values without lowering `quality` or adding metadata flags
- Fusion and agents must treat low `quality` as first-class input
- Future: `metadata.missing_channels: []` standard field (Phase 1+)

## Validators (Phase 0)

Implemented in Pydantic models:

- `confidence` and `quality` between 0 and 1
- `latency_ms` non-negative
- Required strings non-empty
- `SensorEventV1.values` non-empty

## Future Migration v1 → v2

1. Introduce `SensorEventV2` alongside v1
2. Dual-publish during migration window
3. Update consumers with feature flag
4. Deprecate v1 with documented sunset date in ADR
5. Archive sample v1 payloads in Evidence Center

## Phase 0 Note

Schemas are implemented and tested. No runtime ingest validates live streams yet.
