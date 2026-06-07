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
