# Redis Stream Registry

AXON uses the `axon:v1:stream:` namespace consistently across phases.

| Stream Name | Producer | Consumer | Schema | MAXLEN (approx) |
|-------------|----------|----------|--------|-----------------|
| `axon:v1:stream:sensors:emg` | axon-api (MQTT ingest) | edge-inference, agent loop | SensorEventV1 | 1000 |
| `axon:v1:stream:sensors:ecg_like` | axon-api | agent loop | SensorEventV1 | 1000 |
| `axon:v1:stream:sensors:imu` | axon-api | edge-inference, agent loop | SensorEventV1 | 1000 |
| `axon:v1:stream:sensors:spo2_proxy` | axon-api | agent loop | SensorEventV1 | 1000 |
| `axon:v1:stream:robot_state` | axon-api | agent loop | SensorEventV1 | 1000 |
| `axon:v1:stream:model_scores` | edge-inference | axon-api watcher, agent loop | ModelScoreEventV1 | 1000 |
| `axon:v1:stream:agent_traces` | axon-api agent loop | dashboard WS, REST | AgentTraceEventV1 | 1000 |
| `axon:v1:stream:decisions` | axon-api agent loop, HITL | dashboard WS, REST | DecisionEventV1 | 1000 |
| `axon:v1:stream:alerts` | axon-api agent loop | dashboard (future) | alert payload | 500 |

## Pending Decision Keys (Redis, not streams)

| Key Pattern | Purpose |
|-------------|---------|
| `axon:v1:pending_decisions` | Set of pending decision IDs |
| `axon:v1:pending_decision:{decision_id}` | Serialized DecisionEventV1 JSON |
