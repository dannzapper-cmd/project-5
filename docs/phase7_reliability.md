# Phase 7 — Reliability Layer

AXON Phase 7 adds a lightweight **reliability layer** on top of the existing API.
It helps operators and reviewers understand whether the simulated system is alive,
ready, degraded, or missing optional evidence — without turning AXON into a heavy
infrastructure platform.

**Safety:** AXON is a **simulated portfolio system**. No real patient data. No
medical diagnosis or treatment claims. Not a medical device.

## Endpoints

| Route | HTTP | Purpose |
|-------|------|---------|
| `/health/live` | 200 | Liveness — API process is alive; does not fail when optional deps are down |
| `/health/ready` | 200 or 503 | Readiness — required vs optional dependency breakdown |
| `/status/services` | 200 | Full component status map for diagnostics |
| `/health` | 200 | Legacy aggregate health (Phase 1–5 fields preserved) |

### HTTP status convention

- **`/health/live`:** always **200** when the API process responds.
- **`/health/ready`:** **200** when aggregate status is `ok` or `degraded` (optional/inactive deps only). **503** when a **required** dependency is in `error` / unreachable.
- **`/status/services`:** always **200** when the API can compute the response; component failures appear in JSON, not as HTTP 500.

## Status vocabulary

Each component uses one of:

| Status | Meaning |
|--------|---------|
| `ok` | Check succeeded |
| `degraded` | Operational but impaired (e.g. telemetry not fully connected) |
| `unavailable` | Expected artifact/service not reachable |
| `inactive` | Profile/module not active by design |
| `error` | Verifiable failure (e.g. required Redis TCP check failed) |

## Required vs optional dependencies

Discovered from the **core Docker profile** and existing architecture:

| Component | Classification | Notes |
|-----------|----------------|-------|
| `api` | Required | API process |
| `redis` | Required for core operation | TCP check + runtime flag |
| `mqtt` | Required for core operation | TCP check + runtime flag |
| `telemetry_pipeline` | Optional (core operation) | Degraded when MQTT/Redis runtime flags false |
| `edge_inference` | Optional profile dependency | Inactive until model scores flow |
| `digital_twin` | Optional | Degraded if broadcast loop not running |
| `agents_hitl` | Optional | Available when API is up |
| `dashboard` | Optional | Separate static server; not probed from API |
| `fl_module` | Evidence-only | Disk check for `federated_report.json` |
| `rl_module` | Evidence-only | Disk check for `rl_report.json` |
| `mlflow` | Optional (`learning` profile) | TCP check when `MLFLOW_HOST` is set; otherwise `inactive` |
| `mlops_evidence` | Evidence-only | Disk check for MLOps registry |
| `ros2` | Optional (`ros2` profile) | Inactive when bridge offline |
| `ros2_nav_slam` | Optional (`ros2-nav-slam` profile) | Inactive when MiniLab bridge offline |

Health code uses **TCP checks (≤1s timeout)** and **artifact stat checks** only.
It does **not** import Flower, Gymnasium, SB3, torch, or ROS2 Python packages.

## Running reliability checks

```bash
# With core profile running:
python scripts/reliability/check_phase7_reliability.py --api-base http://localhost:8000

# Offline (artifact scaffolding only, no live API):
python scripts/reliability/check_phase7_reliability.py --offline
```

## Evidence artifacts

| File | Description |
|------|-------------|
| `artifacts/reliability/phase7a_reliability_report.json` | Overall check summary with `run_id`, `phase`, `checks` |
| `artifacts/reliability/service_status_snapshot.json` | Last `/status/services` snapshot |
| `artifacts/reliability/failure_replay_report.json` | Optional-evidence failure scenarios |

## Tests

```bash
pytest tests/phase7/test_phase7_reliability.py -v
```
