# Topic Taxonomy

AXON uses versioned naming across MQTT, Redis Streams, WebSockets, and future ROS2 interfaces.

**Version prefix:** `v1` (increment on breaking contract changes)

## MQTT Topics

| Topic Pattern | Payload Contract | Owner |
|---------------|------------------|-------|
| `axon/v1/sensors/emg/{node_id}` | `SensorEventV1` | sensor-generators |
| `axon/v1/sensors/ecg-like/{node_id}` | `SensorEventV1` | sensor-generators |
| `axon/v1/sensors/imu/{node_id}` | `SensorEventV1` | sensor-generators |
| `axon/v1/sensors/spo2-proxy/{node_id}` | `SensorEventV1` | sensor-generators |
| `axon/v1/robot/state/{robot_id}` | `SensorEventV1` (`robot_state`) | sensor-generators |
| `axon/v1/environment/{zone_id}` | `SensorEventV1` (`environment`) | sensor-generators |
| `axon/v1/alerts/{severity}` | `DecisionEventV1` or alert extension | agent-orchestrator |
| `axon/v1/decisions/{session_id}` | `DecisionEventV1` | agent-orchestrator |
| `axon/v1/agents/traces/{agent_id}` | `AgentTraceEventV1` | agent-orchestrator |

### MQTT Conventions

- Use `/` separators; lowercase segments
- `node_id`, `robot_id`, `zone_id`, `session_id`, `agent_id` are alphanumeric + hyphen
- QoS 1 recommended for telemetry (Phase 1+)

## Redis Stream Names

| Stream | Primary Event Type |
|--------|-------------------|
| `axon:v1:stream:sensors:emg` | `SensorEventV1` |
| `axon:v1:stream:sensors:ecg_like` | `SensorEventV1` |
| `axon:v1:stream:sensors:imu` | `SensorEventV1` |
| `axon:v1:stream:sensors:spo2_proxy` | `SensorEventV1` |
| `axon:v1:stream:robot_state` | `SensorEventV1` |
| `axon:v1:stream:environment` | `SensorEventV1` |
| `axon:v1:stream:model_scores` | `ModelScoreEventV1` |
| `axon:v1:stream:fusion` | Fusion state (future schema) |
| `axon:v1:stream:decisions` | `DecisionEventV1` |
| `axon:v1:stream:agent_traces` | `AgentTraceEventV1` |
| `axon:v1:stream:alerts` | Alert events |
| `axon:v1:stream:health` | `HealthEventV1` |

### Redis Conventions

- Use `:` separators (Redis community practice)
- Consumer groups named `axon-{service}-cg` (Phase 1+)
- Stream IDs enable replay from arbitrary offsets

## WebSocket Channels

| Channel | Event Types Broadcast |
|---------|----------------------|
| `/ws/v1/sensors` | `SensorEventV1` |
| `/ws/v1/robot-state` | `SensorEventV1` (robot_state) |
| `/ws/v1/fusion` | Fusion state (stream mirror; Phase 5 uses `/ws/v1/twin`) |
| `/ws/v1/twin` | `DigitalTwinStateV1` (Phase 5) |
| `/ws/v1/decisions` | `DecisionEventV1` |
| `/ws/v1/agents` | `AgentTraceEventV1` |
| `/ws/v1/alerts` | Alerts |
| `/ws/v1/health` | `HealthEventV1` |

## Future ROS2 Interfaces

### Topics

| Topic | Message Contract |
|-------|------------------|
| `/axon/sensors/emg` | AXON sensor message (TBD Phase 5) |
| `/axon/sensors/ecg_like` | AXON sensor message |
| `/axon/sensors/imu` | AXON sensor message |
| `/axon/sensors/spo2_proxy` | AXON sensor message |
| `/axon/robot/state` | Robot state |
| `/axon/fusion/state` | Fusion output |
| `/axon/alerts` | Alerts |
| `/axon/agent_traces` | Agent traces |
| `/axon/nav/status` | Navigation status |

### Services / Actions

| Interface | Type | Purpose |
|-----------|------|---------|
| `/axon/safety/request_operator_confirmation` | Service | HITL gate |
| `/axon/robot/pause_session` | Service | Safety pause |
| `/axon/nav/execute_rehab_route` | Action | Nav2 rehab route |

## Naming Conventions

1. **Prefix:** all interfaces start with `axon` and version `v1`
2. **Signal names:** `ecg_like` in Redis/ROS2; `ecg-like` in MQTT URLs
3. **IDs in paths:** replace `{node_id}` etc. with stable simulator IDs
4. **Ownership:** publishing service owns schema compliance for its topics

## Versioning Rules

- **Patch:** additive optional fields in JSON payload — same `v1`
- **Minor:** new streams/topics — may stay `v1` if backward compatible
- **Major:** breaking field changes — bump to `v2`, run dual-publish migration window

## Payload Contract Ownership

| Layer | Owns |
|-------|------|
| `apps/api/app/schemas/events.py` | Canonical Pydantic models |
| `docs/schemas/event-contracts.md` | Human-readable contract spec |
| Service READMEs | Topic/stream publish/subscribe roles |

## Replay Implications

- Replay must preserve original `event_id` and `trace_id` unless explicitly generating synthetic replay markers in metadata
- Stream offsets documented in replay runbooks (Phase 1+)
- WebSocket replay mode flags `metadata.replay=true` (future)

## Trace ID Propagation Rules

1. **Origin:** first ingest assigns or accepts `trace_id` from scenario session
2. **Propagation:** all derived events (scores, fusion, decisions, traces) reuse parent `trace_id`
3. **Child traces:** agent sub-workflows may append suffix (e.g., `trace-abc:agent-step-2`) — must reference parent in `related_event_ids`
4. **Breakage:** changing `trace_id` mid-pipeline requires `metadata.trace_fork_reason`

## Phase 0 Note

Taxonomy is defined. No brokers or streams are wired yet.
