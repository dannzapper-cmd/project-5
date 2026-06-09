# Fresh Clone Demo Checklist

*Reproducing the AXON core demo from a clean machine.*

---

## Purpose

This checklist helps reviewers, auditors, and contributors reproduce AXON's **default demo path** from a **fresh clone** on a new machine using local tools and Docker Compose. It reduces "works on my machine" risk by documenting prerequisites, commands, expected healthy signals, and honest scope boundaries.

AXON is **simulated-only**, **synthetic-only**, **local-first**, and **evidence-backed**. The core profile demo is **bounded** to a synthetic rehab robot operations scenario — not a universal platform for arbitrary real-world data.

---

## What this checklist proves

| Proof point | How |
|-------------|-----|
| Core profile starts from a fresh clone | `docker compose --profile core up -d --build` succeeds |
| Local model artifacts can be recreated | `make models-generate` produces gitignored ONNX files required for the stack |
| API, dashboard, and telemetry health | Verification script hits documented endpoints |
| Demo evidence is comparable | Committed Phase 10A screenshots and runbook describe the same path |
| Heavier profiles are optional | ROS2/Nav2/SLAM, FL/RL/MLOps are **not** required for the default reviewer demo |

---

## What this checklist does not prove

| Not proven | Why it matters |
|------------|----------------|
| Enterprise production readiness | AXON is not enterprise-production-ready today |
| Hardware or field validation | Core demo uses synthetic generators only |
| Clinical or medical readiness | AXON is not a medical device, not for clinical use, and does not diagnose or treat any condition |
| Cloud, Kubernetes, or VM deployment | Local Compose is the reproducible baseline |
| All optional profiles running at once | Profiles are modular by design — see [profiles.md](../../../architecture/profiles.md) |
| Non-synthetic health records | Synthetic biomedical-inspired signals only; no real patient data |
| Arbitrary real-world data ingestion | Bounded scenario requires adapters, validation, and safety review for non-synthetic sources |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Git** | Clone the repository |
| **Docker Desktop or Docker Engine** | Must be running before `docker compose` |
| **Python 3.12** | For venv, verification helpers, optional screenshot tools |
| **Make** | `make models-generate` and `make lint` |
| **Shell** | Bash-compatible environment for repo scripts |
| **Local resources** | Enough CPU/RAM for the core Docker profile (see troubleshooting) |
| **Ports available** | **3000** (dashboard), **8000** (API); internal: **1883** (MQTT), **6379** (Redis) |

**Windows:** WSL2 or Git Bash is recommended for bash scripts such as `phase10a_verify_demo.sh`.

---

## Fresh clone steps

```bash
git clone https://github.com/dannzapper-cmd/project-5.git
cd project-5
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,edge-ai,agents,mlops]"

# Required before Docker build — ONNX models are gitignored
make models-generate

docker compose --profile core up -d --build
```

Wait **30–60 seconds** for MQTT, Redis, API health, and live synthetic telemetry.

```bash
ASSUME_UP=true bash scripts/demo/phase10a_verify_demo.sh
```

Open in a browser:

- Dashboard: http://localhost:3000
- API health: http://localhost:8000/health
- Telemetry status: http://localhost:8000/telemetry/status

**Stop when finished:**

```bash
docker compose --profile core down
```

---

## Expected healthy result

After warm-up, expect the following:

| Signal | Expected |
|--------|----------|
| Docker services | `docker compose --profile core ps` shows core services up (api, dashboard, redis, mosquitto, sensor-generators, edge-inference) |
| Dashboard | http://localhost:3000 loads the operational dashboard |
| API health | `GET /health` returns HTTP 200 |
| Telemetry | `GET /telemetry/status` returns HTTP 200; `received_events` increases after warm-up |
| Model scores | `GET /model-scores/status` returns HTTP 200; scores increment during live synthetic streams |
| Mission | `GET /mission/status` returns HTTP 200 |
| Verification script | Log ends with **`OVERALL: PASS`** and **Critical failures: 0** |
| Dashboard panels | Synthetic telemetry, digital twin, agent/HITL, and evidence/observability panels populate depending on runtime state |

The verification script also checks `/health/live`, `/health/ready`, `/status/services`, and dashboard `/` — all critical checks must pass for `OVERALL: PASS`.

Optional endpoints (warnings only if unavailable): `/mission/status`, twin status, Nav2/SLAM status, `/metrics`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `docker compose` fails immediately | Docker not running | Start Docker Desktop or the Docker daemon |
| `python3.12` not found | Python 3.12 not installed | Install Python 3.12; recreate `.venv` with that interpreter |
| Port bind errors on 3000 or 8000 | Another process using ports | Stop conflicting services or set `DASHBOARD_PORT` / `API_PORT` if your environment supports overrides |
| Edge inference or API fails on build | ONNX models missing | Run `make models-generate` before `docker compose up` |
| Endpoints return errors right after `up` | Services still warming up | Wait 30–60 seconds; re-run verification |
| Dashboard loads but some panels empty | Warm-up incomplete or WebSocket not connected | Refresh after 60s; confirm API health and telemetry counters |
| Verification fails immediately | Stack not up or wrong directory | Confirm `docker compose --profile core ps`; run from repo root |
| Playwright screenshot recapture fails | Playwright/Chromium not installed | `pip install playwright && playwright install chromium` (optional path only) |
| ROS2/Nav2/SLAM appears offline | Expected under `core` only | Start `ros2` or `ros2-nav-slam` profiles explicitly if needed — not required for this checklist |
| FL/RL/MLOps panels artifact-only | Expected under `core` only | Run `learning` profile on demand; artifacts may show `not_generated` in core UI |
| Slow machine / low memory | Resource contention | Close other heavy apps; allow longer warm-up; allocate more RAM to Docker |

---

## Optional screenshot validation

Committed Phase 10A screenshots live under:

`docs/evidence/phase10/demo/screenshots/latest/`

**Validate existing PNG evidence (no browser required):**

```bash
.venv/bin/python scripts/demo/validate_phase10a_screenshots.py
```

**Recapture screenshots only if fresh local evidence is desired (optional):**

```bash
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python scripts/demo/capture_phase10a_screenshots.py
.venv/bin/python scripts/demo/validate_phase10a_screenshots.py
```

Screenshot recapture is **not required** to run or verify the core demo.

---

## Bounded demo notes

AXON's demo path is **intentionally bounded** to a **synthetic rehab robot operations** scenario. It demonstrates telemetry ingest, edge-like inference, agent coordination, digital twin mirroring, and evidence governance under **local-first, profile-based** constraints.

This bounded scope is a **strength for reproducibility**: reviewers get a consistent, script-verified path without depending on author-specific configuration, real hardware, or external data sources.

AXON is **not** meant to accept arbitrary real biomedical or robotics data without adapters, schema validation, and safety review. Optional profiles (`obs`, `learning`, `ros2`, `ros2-nav-slam`, `llm`, `full`) extend the system but are **not required** for the default reviewer demo.

---

## Clean teardown

```bash
docker compose --profile core down
```

**Optional — removes volumes (Redis/MQTT persisted state):**

```bash
docker compose --profile core down -v
```

Use `-v` only when a clean slate is intentional; it deletes local stream buffer state.

---

## Related evidence

| Artifact | Link |
|----------|------|
| Phase 10A runbook | [runbook-phase10a.md](runbook-phase10a.md) |
| Demo verification report | [demo-verification-report.md](demo-verification-report.md) |
| Screenshot index | [screenshot-index.md](screenshot-index.md) |
| Phase 10 index | [../README.md](../README.md) |
| Evidence Center | [../../README.md](../../README.md) |
| Project README | [../../../../README.md](../../../../README.md) |
| Compose profiles | [../../../architecture/profiles.md](../../../architecture/profiles.md) |
| Production path (planning) | [../../../production/README.md](../../../production/README.md) |
