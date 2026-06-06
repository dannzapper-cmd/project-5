# AXON API Gateway

FastAPI async gateway for the AXON Bio-Robotics Edge Command System.

## Phase 0 Status

- `GET /health` — service health and phase metadata
- Pydantic event schemas defined (not yet exposed via routes)
- No telemetry, WebSocket, or inference routes yet

## Future Phases

| Phase | Capability |
|-------|------------|
| 1 | MQTT ingest, Redis Streams buffer, WebSocket broadcast |
| 2 | ONNX Runtime inference hooks |
| 3 | Agent orchestration endpoints |
| 7 | OpenTelemetry instrumentation |

## Local Development

```bash
make api
# or
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker

Started via `make compose-core` under the `core` profile.
