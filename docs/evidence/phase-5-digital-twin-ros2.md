# Phase 5 Evidence Checklist — Digital Twin + ROS2 Core

Synthetic signals only. No medical diagnosis. No Nav2/SLAM in this phase.

## Required Screenshots (E1–E8)

| ID | Scenario | Expected | Capture |
|----|----------|----------|---------|
| E1 | Twin normal | mode assisting, 4 sensors, high confidence | Dashboard screenshot |
| E2 | Twin warning | EMG/ECG anomaly, elevated risk | Dashboard screenshot |
| E3 | Twin degraded | sensor dropout, mode degraded | Dashboard screenshot |
| E4 | HITL / safety pause | HITL pending, paused, blocked reason | Dashboard screenshot |
| E5 | ROS2 topic echo | `/axon/twin/state` JSON with updating timestamps | Terminal screenshot |
| E6 | Backend health | `/health` 200 with `twin_service` + `ros2_bridge` | `curl` output |
| E7 | Test suite | `make test` zero failures | Terminal screenshot |
| E8 | Staleness transition | active → stale → dropout within TTL | Video or two screenshots |

## Commands

```bash
git checkout feat/phase-5-digital-twin-ros2-core
make install
make test
docker compose --profile core up --build -d
# Dashboard: http://localhost:3000
make replay-normal
make replay-fatigue
make replay-dropout
docker compose --profile core --profile ros2 up --build -d
docker compose --profile ros2 exec ros2_bridge ros2 topic echo /axon/twin/state
curl -s http://localhost:8000/health | python3 -m json.tool
```

## QA-LIVE Steps

- **QA-LIVE-1:** Core up, generators running, twin updates in browser within 1s
- **QA-LIVE-2:** Stop generators; stale within `SENSOR_STALE_TTL_SECONDS`; dropout within `SENSOR_DROPOUT_TTL_SECONDS`; mode degraded
- **QA-LIVE-3:** Replay scenarios produce visible twin changes

## Local QA Run — 2026-06-07

Branch: `feat/phase-5-digital-twin-ros2-core`

Base verified before fixes: `959fccb`

Environment:

- OS: macOS Darwin 25.5.0
- Docker: Docker Desktop 4.76.0, Engine 29.5.2
- Docker Compose: v5.1.4
- Python: `python3.12` for repo venv; host `python3` 3.14.5 also present
- Node: v22.22.0
- Browser: Cursor browser against `http://localhost:3000`

### Commands Verified

| Command | Result | Notes |
|---|---|---|
| `git status && git fetch origin && git switch feat/phase-5-digital-twin-ros2-core && git pull --ff-only` | PASS | Clean verification clone, branch tracked `origin/feat/phase-5-digital-twin-ros2-core`. |
| `make install` | PASS | Installed dev, edge-ai, agents, and mlops extras into `.venv`. |
| `make test` | PASS | Final result: 94 passed, 2 warnings. |
| `make lint` | PASS | Ruff passed. |
| `make compose-config` | PASS | Core profile config valid. |
| `make compose-ros2` | PASS | Core + ROS2 profile config valid. |
| `make models-generate` | PASS | `emg_anomaly_v0` and `imu_movement_v0` generated and validated. |
| `docker compose --profile core up --build -d` | PASS | Core services healthy; dashboard served on port 3000. |
| `curl -s http://localhost:8000/health \| python3 -m json.tool` | PASS | `twin_service.running=true`; ROS2 reports offline before ros2 profile and connected after bridge start. |
| `curl -s http://localhost:8000/api/v1/twin/state \| python3 -m json.tool` | PASS | Returned `DigitalTwinStateV1` with 4 sensor nodes. |
| `docker compose --profile core stop sensor-generators` | PASS | Active -> stale at ~6s; stale -> dropout at ~17s. |
| `docker compose --profile core up -d sensor-generators` | PASS | Sensors recovered to active without full core restart. |
| `make replay-normal` | PASS | Replay published successfully; twin returned nominal active state. |
| `make replay-fatigue` | PASS | Replay published successfully; fixed profile now produces warning/degraded evidence. |
| `make replay-dropout` | PASS | Replay published successfully; TTL/dropout path remains functional. |
| `POST /api/v1/twin/command` pause / safety stop / resume | PASS | Versioned responses with `trace_id`; blocked resume reason present during safety stop. |
| `docker compose --profile core --profile ros2 up --build -d` | PASS | `ros2_bridge` builds and runs in `ros2` profile. |
| `docker compose --profile ros2 exec ros2_bridge ros2 topic list` | PASS | `/axon/twin/state` present. |
| `docker compose --profile ros2 exec ros2_bridge ros2 topic echo /axon/twin/state` | PASS | JSON payloads with moving timestamps; not hello-world. |
| `docker compose --profile ros2 exec ros2_bridge ros2 service call /axon/command ...` | PASS | `/axon/command` returned accepted response with trace id. |

### Evidence Results

| ID | Result | Evidence |
|---|---|---|
| E1 Twin normal | PASS | `/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/e1-twin-normal-fixed.png` |
| E2 Twin warning | PASS | `/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/e2-fatigue-warning-state.png` |
| E3 Twin degraded | PASS | `/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/e3-degraded-digital-twin-panel.png` |
| E4 HITL / safety pause | PASS | `/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/e4-hitl-safety-pause.png` |
| E5 ROS2 topic echo | PASS | Terminal output captured from `ros2 topic echo /axon/twin/state`, timestamps advanced from `17:21:44` through `17:21:48`. |
| E6 Backend health | PASS | `/health` returned `twin_service.running=true` and `ros2_bridge.status=connected`. |
| E7 Test suite | PASS | `make test`: 94 passed, 2 warnings. |
| E8 Staleness transition | PASS | `/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/e8-staleness-transition-stale.png` and `/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/e8-staleness-transition-dropout.png` |

### Fixes Applied During QA

- Digital twin risk/mode derivation now degrades on dropout/corrupt sensor nodes even when confidence remains high.
- Dashboard SVG class updates now use `setAttribute("class", ...)`, so sensor status colors render for active/stale/dropout states.
- `fatigue_event` replay quality was lowered to trigger a reproducible warning/degraded synthetic state.
- ROS2 package build no longer creates duplicate `ament_cmake_python` targets.
- ROS2 bridge logging uses a supported `rclpy` logger call.
- `ros2_bridge` can be managed with `docker compose --profile ros2 logs/exec ...` while still remaining outside the core profile.

### Scope / Claims Audit

Result: PASS.

No Phase 6 implementation, no Phase 5.5 implementation, no Nav2/SLAM runtime, no federated learning, no RL, no cloud/VM runtime, no hardware integration, no real patient data, and no positive medical claims were added. Matches for medical/scope terms are policy disclaimers, roadmap placeholders, or explicit out-of-scope statements.
