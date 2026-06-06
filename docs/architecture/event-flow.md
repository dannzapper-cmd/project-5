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

## Phase 0 Note

Event flow is documented and schema contracts exist. No runtime pipeline is wired yet.
