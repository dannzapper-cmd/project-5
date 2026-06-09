# Phase 10A Demo Runbook — Visual Automation

**Local-only · Synthetic-only · Core profile**

## Prerequisites

- Docker Desktop (or Docker Engine) running
- Python 3.12 with project venv (`.venv`)
- ONNX models generated locally: `make models-generate`
- Playwright Chromium (one-time): `.venv/bin/pip install playwright && .venv/bin/playwright install chromium`
- Optional Node.js path: `cd scripts/demo && npm install && npm run install-browsers` (if Node is available)

## Branch / commit

- Branch: `feat/phase-10a-demo-automation`
- Base after PR #17: `f8d5e1b643a122bf6197ecef9f3818f2933df841`

## Profiles used

| Profile | Required for 10A | Notes |
|---------|------------------|-------|
| `core` | **Yes** | API, dashboard, MQTT, Redis, sensors, edge inference |
| `obs` | No | Optional; not started in 10A capture |
| `learning` | No | On-demand FL/RL; artifact-only in mission panel |
| `ros2` | No | Bridge offline under core-only |
| `ros2-nav-slam` | No | Compose-validated; dashboard shows **offline** |

## Start stack

```bash
git checkout feat/phase-10a-demo-automation
make models-generate   # if models/onnx/ missing
docker compose --profile core up -d --build
```

Wait 30–60 seconds for MQTT, Redis, API health, and live telemetry.

## Verify

```bash
# Full verify (starts stack if ASSUME_UP unset)
bash scripts/demo/phase10a_verify_demo.sh

# Stack already running
ASSUME_UP=true bash scripts/demo/phase10a_verify_demo.sh
```

### Expected ports

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Dashboard | http://localhost:3000 |
| MQTT | localhost:1883 |
| Redis | localhost:6379 |

### Critical health endpoints

- `GET /health` — 200
- `GET /health/live` — 200
- `GET /health/ready` — 200
- `GET /status/services` — 200
- `GET /telemetry/status` — 200, `received_events` > 0 after warm-up
- `GET /model-scores/status` — 200, scores incrementing
- `GET /mission/status` — 200
- Dashboard `GET /` — 200

## Capture screenshots

**Primary (Python — no Node required):**

```bash
.venv/bin/python scripts/demo/capture_phase10a_screenshots.py
```

**Alternate (Node, if installed):**

```bash
cd scripts/demo && npm run capture
```

Output:

- `docs/evidence/phase10/demo/screenshots/<timestamp>/`
- `docs/evidence/phase10/demo/screenshots/latest/` (copies of latest run)

Validate PNG evidence (stdlib, no Pillow required):

```bash
.venv/bin/python scripts/demo/validate_phase10a_screenshots.py
```

## Stop / cleanup

```bash
docker compose --profile core down
# optional: docker compose --profile core down -v
```

## Expected screenshots

| File | Proves |
|------|--------|
| `00_dashboard_overview.png` | Connection status, WebSocket indicators |
| `01_live_telemetry_streams.png` | EMG, ECG-like, IMU, SpO2-proxy cards |
| `02_edge_inference_and_fusion.png` | Live ONNX model scores |
| `03_agent_traces_and_hitl.png` | Agent traces + decision/HITL context |
| `04_digital_twin_state_mirror.png` | Digital twin SVG + metadata |
| `05_evidence_center_or_observability.png` | Phase 7 ops status + Phase 8 mission/evidence |
| `06_failure_or_degraded_mode_if_available.png` | Simulated failure injection UI |
| `07_ros2_nav_slam_compose_status_if_available.png` | MiniLab **offline** under core-only |

## Known risks / limitations

- ROS2 bridge and Nav2/SLAM MiniLab are **offline** unless their profiles are started — compose-validated, not live-gated in core demo.
- FL/RL/MLOps panels may show artifact-only or idle unless on-demand scripts were run.
- ONNX models are gitignored; `make models-generate` is required on fresh clones.
- Dashboard is static HTML/JS via `python -m http.server` — not a SPA build pipeline.
- Video script / shot list intentionally **not** in repo (Phase 10B boundary).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Docker not running | Start Docker Desktop; retry `docker compose --profile core up` |
| Port in use | `lsof -i :8000` / `:3000`; stop conflicting process or set `API_PORT` / `DASHBOARD_PORT` |
| Dashboard blank counters | Wait 30s; check `curl localhost:8000/telemetry/status` |
| API health failing | `docker compose --profile core logs api --tail=100` |
| WebSocket dots offline | Normal until browser opens dashboard; refresh after API healthy |
| Playwright browser missing | `.venv/bin/playwright install chromium` |
| Slow startup | API healthcheck `start_period` 15s; allow 60s before screenshots |
| Edge inference build fail | Run `make models-generate` first |

## Claims safety

- Synthetic biomedical-inspired signals only
- Simulated rehab robot operations — not a medical device
- No clinical diagnosis, treatment, or prevention claims
- Use **synthetic retraining / candidate refresh loop** for MLOps wording
- ROS2/Nav2/SLAM: **compose-validated** unless profile explicitly started
