# AXON API Gateway

FastAPI async gateway for the AXON Bio-Robotics Edge Command System.

## Phase 1 Status

| Endpoint / Channel | Status |
|--------------------|--------|
| `GET /health` | Phase metadata + connectivity flags |
| `GET /telemetry/status` | Counters, stream mapping, MQTT/Redis state |
| MQTT subscriber | Background task with retry/reconnect |
| Redis Streams | Append with MAXLEN ~1000 per stream |
| `/ws/v1/sensors` | Live sensor events |
| `/ws/v1/robot-state` | Robot state events |
| `/ws/v1/health` | Health/status channel |

## Data Flow

```
MQTT (aiomqtt) → Pydantic validation → Redis Streams (redis.asyncio) → WebSocket broadcast
```

## Configuration

| Variable | Default |
|----------|---------|
| `REDIS_URL` | redis://localhost:6379/0 |
| `MQTT_HOST` | localhost |
| `MQTT_PORT` | 1883 |
| `AXON_PHASE` | 1 |

## Local Development

```bash
# Requires Mosquitto + Redis running
make api
curl http://localhost:8000/health
curl http://localhost:8000/telemetry/status
```

## Docker

Started via `make compose-core` under the `core` profile.

## Not Implemented (Future Phases)

- ONNX inference routes
- Agent orchestration
- OpenTelemetry instrumentation (Phase 7)
