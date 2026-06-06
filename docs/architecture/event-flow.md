# Event Flow

End-to-end flow for synthetic telemetry through AXON to the dashboard and Evidence Center.

## Primary Flow

```mermaid
sequenceDiagram
    participant SG as Synthetic Sensors
    participant MQ as MQTT / Mosquitto
    participant API as FastAPI Gateway
    participant RS as Redis Streams
    participant INF as Edge Inference
    participant FUS as Fusion Service
    participant AGT as LangGraph Agents
    participant LC as LangChain Tools
    participant WS as WebSocket Broadcast
    participant DASH as Dashboard
    participant EV as Evidence Center

    SG->>MQ: Publish SensorEventV1
    MQ->>API: Ingest + validate
    API->>RS: Append to stream (trace_id)
    RS->>INF: Consume sensor batch
    INF->>RS: ModelScoreEventV1
    RS->>FUS: Multi-modal fusion
    FUS->>RS: Fusion state event
    RS->>AGT: Trigger evaluation
    AGT->>LC: Tool / RAG calls
    LC-->>AGT: Context + results
    AGT->>RS: DecisionEventV1 + AgentTraceEventV1
    API->>WS: Broadcast updates
    WS->>DASH: Live UI update
    AGT->>EV: Trace + decision artifacts
    INF->>EV: Latency benchmarks
```

## Replay Mode (Future)

```mermaid
flowchart LR
    RS[Redis Streams Archive]
    RP[Replay Controller]
    API[API Gateway]
    CON[Downstream Consumers]

    RS --> RP
    RP --> API
    API --> CON
```

Replay re-emits historical events with preserved `trace_id` for deterministic debugging and demo reproduction.

## Trace ID Propagation

Every event carries a `trace_id` from first ingest through inference, fusion, agents, and dashboard broadcast. Downstream services must propagate the same `trace_id` unless spawning a child trace (documented in agent traces).

## Validation Gate

Validation occurs **before** inference:

1. Schema validation (Pydantic)
2. Quality/confidence bounds check
3. Missing/corrupt data flagged — never silently repaired without lowering confidence

## Phase 2 Runtime (Implemented)

The following path is live under the `core` Docker Compose profile:

1. `sensor-generators` publishes `SensorEventV1` to MQTT
2. `api` subscribes via aiomqtt, validates, appends to Redis Streams
3. `edge-inference` consumes EMG/IMU streams via XREAD BLOCK
4. ONNX Runtime CPU inference produces `ModelScoreEventV1`
5. Model scores appended to `axon:v1:stream:model_scores`
6. `api` model score watcher broadcasts to `/ws/v1/model-scores`
7. Dashboard shows live telemetry and model score panels

Not yet implemented: sensor fusion, agents, decision events.

## Phase 1 Runtime (Implemented)

The telemetry ingest path from Phase 1 remains active:

1. `sensor-generators` publishes `SensorEventV1` to MQTT
2. `api` subscribes via aiomqtt (background reconnect loop)
3. Events validated with Pydantic, appended to Redis Streams (MAXLEN ~1000)
4. WebSocket broadcast to dashboard at `ws://localhost:8000`
5. Replay via `replay/replay_publish.py` → MQTT (same ingest path)
