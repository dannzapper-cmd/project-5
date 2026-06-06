# AXON Tests

## Phase 0 Scope

Phase 0 tests validate **contracts only** — no Docker, Redis, MQTT, or frontend required.

| Test file | Coverage |
|-----------|----------|
| `test_schemas.py` | Pydantic v2 event schema validation |

## Running Tests

```bash
make test
# or
pytest tests/
```

## Future Phases

- Phase 1: MQTT ingest, Redis Streams, WebSocket integration tests
- Phase 2: ONNX inference latency benchmarks
- Phase 3: Agent trace contract tests
- Phase 7: Observability exporter smoke tests

Integration tests that require external services should be marked and run under appropriate Docker Compose profiles.
