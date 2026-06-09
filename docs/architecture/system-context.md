# System Context

AXON operates in a simulated rehabilitation robotics operations scenario. Operators interact through a dashboard while edge services process synthetic telemetry, run inference, coordinate agents, and emit evidence.

## Context Diagram

```mermaid
flowchart TB
    subgraph Operators
        OP[Operator / Reviewer]
    end

    subgraph AXON["AXON Platform"]
        DASH[Dashboard + Digital Twin]
        API[FastAPI Gateway + WebSockets]
        MQTT[MQTT / Mosquitto]
        REDIS[Redis Streams + Replay]
        INF[Edge Inference ONNX Runtime]
        FUS[Fusion Service]
        AGT[LangGraph Agent Orchestrator]
        LC[LangChain Tools / RAG Layer]
        LEARN[Learning Layer MLflow / Flower / RL]
        OBS[OpenTelemetry / Prometheus / Grafana]
        ROS[ROS2 Thin Adapter]
        DT[Digital Twin Renderer]
    end

    subgraph Synthetic["Synthetic IoT Layer"]
        SENS[Synthetic Sensor Generators]
        ROB[Simulated Robot State]
    end

    OP --> DASH
    DASH <--> API
    SENS --> MQTT
    ROB --> MQTT
    MQTT --> API
    API --> REDIS
    REDIS --> INF
    INF --> FUS
    FUS --> AGT
    AGT --> LC
    AGT --> API
    API --> DASH
    LEARN -.-> INF
    LEARN -.-> AGT
    OBS -.-> API
    OBS -.-> INF
    OBS -.-> AGT
    FUS --> ROS
    AGT --> ROS
    API --> DT
    DT --> DASH
```

## Component Responsibilities

| Component | Responsibility | Phase |
|-----------|----------------|-------|
| Synthetic sensors | Generate biomedical-inspired telemetry | 1 |
| MQTT broker | Pub/sub ingress | 1 |
| API gateway | Validate, route, WebSocket broadcast | 1 |
| Redis Streams | Buffer, replay, consumer groups | 1 |
| Edge inference | ONNX Runtime scoring | 2 |
| Fusion | Multi-sensor state + confidence | 2 |
| Agent orchestrator | LangGraph stateful workflows | 3 |
| LangChain layer | Tools, RAG, retrievers | 3 |
| Learning | MLflow, synthetic retraining / candidate refresh loop, Flower, RL | 4, 6 |
| Observability | Traces, metrics, dashboards | 7 |
| ROS2 bridge | Robotics integration | 5, 5.5 |
| Digital twin | Live visualization | 5 |

## Phase 0 Note

Only the API health endpoint and schema contracts exist today. This diagram is the **target architecture**.
