# AXON Tests

## Phase 1 Scope

Unit tests validate contracts and telemetry spine logic without Docker, MQTT, or Redis.

| Test file | Coverage |
|-----------|----------|
| `test_schemas.py` | Pydantic v2 event schema validation |
| `test_generators.py` | Synthetic sensor event generation |
| `test_topic_router.py` | MQTT topic → Redis stream mapping |
| `test_websocket_format.py` | WebSocket payload serialization |
| `test_replay_jsonl.py` | Pre-generated replay scenario files |

## Running Tests

```bash
make test
```

Regenerate replay files before testing if scenarios change:

```bash
make replay-generate
```

## Future Phases

- Phase 2: ONNX inference benchmarks
- Phase 3: Agent trace contract tests
- Integration tests with Docker Compose profile markers
