# Demo Runbook (Placeholder)

## Phase 0 Demo — Foundation Validation

This runbook validates Phase 0 skeleton only. It does **not** demonstrate telemetry, ML, or agents.

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git clone of AXON repository

### Steps

```bash
# 1. Virtual environment and dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Schema tests
make test

# 3. Dev check
make dev-check

# 4. Validate Compose config
make compose-config

# 5. Start core profile (optional)
make compose-core
```

### Expected Results

| Step | Evidence |
|------|----------|
| `make test` | All schema tests pass |
| `make dev-check` | Success message printed |
| `make compose-config` | Valid YAML output, exit 0 |
| `make compose-core` | API health at `http://localhost:8000/health` |
| Dashboard | Static placeholder at `http://localhost:8080` |

### Health Check

```bash
curl http://localhost:8000/health
```

Expected:

```json
{
  "status": "ok",
  "service": "axon-api",
  "phase": 0,
  "version": "0.1.0"
}
```

### What This Demo Does NOT Show

- Live MQTT telemetry
- Redis Streams consumption
- WebSocket updates
- ONNX inference
- LangGraph agents
- Digital twin
- ROS2 / Nav2 / SLAM

See [ROADMAP.md](../../ROADMAP.md) for Phase 1+ demos.
