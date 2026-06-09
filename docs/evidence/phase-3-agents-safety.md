# Phase 3 — Agents + Safety Evidence

## Checklist

- [ ] Core mode running (`docker compose --profile core up --build`)
- [ ] Agent traces visible (dashboard + `/api/v1/agents/traces`)
- [ ] Current decision visible (`/api/v1/decisions/current`)
- [ ] High-risk or low-confidence HITL visible (failure injection buttons)
- [ ] Mock LLM copilot explanation visible in decision rationale
- [ ] Optional real LLM demo if keys configured (`AXON_LLM_MODE=real`)
- [ ] Failure injection screenshot (sensor_dropout / model_low_confidence)
- [ ] Redis stream inspection (`XLEN axon:v1:stream:agent_traces`)
- [ ] Tests passing (`make test-phase-regression`)
- [ ] Docker running without real LLM keys
- [ ] PR link attached

## Artifacts (committed)

| Artifact | Path |
|----------|------|
| Graph topology (Mermaid) | [phase-3-agent-graph.md](./phase-3-agent-graph.md) |
| HITL trace sample JSON | [phase-3-trace-sample.json](./phase-3-trace-sample.json) |
| Mock-mode benchmarks | [phase-3-benchmarks.md](./phase-3-benchmarks.md) |

## Generate Evidence

```bash
make install
make evidence-phase3
make test-phase-regression
docker compose --profile core up --build
```

## Verification Commands

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/agents/traces
curl http://localhost:8000/api/v1/decisions/current
curl http://localhost:8000/api/v1/safety/status
redis-cli XLEN axon:v1:stream:agent_traces
redis-cli XLEN axon:v1:stream:decisions
```

## Failure Injection Demo

```bash
curl -X POST http://localhost:8000/api/v1/failure-injection/model_low_confidence
curl http://localhost:8000/api/v1/decisions/current
curl -X POST http://localhost:8000/api/v1/failure-injection/reset
```

## Intentionally Not in Scope

- MLflow, synthetic retraining / candidate refresh loop
- ROS2, Nav2, SLAM
- Vector DB / embedding RAG
- Mandatory local LLM (Ollama)
- Real patient data or medical claims
