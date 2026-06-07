# Phase 5.5 Evidence Checklist — ROS2 Nav2 + SLAM MiniLab

Simulated robotics navigation/mapping lab. **No physical robot. No patient data.
No medical claims. No clinical autonomy.** Synthetic signals only.

- Compose service name: `ros2_nav_slam`
- Profile: `ros2-nav-slam`
- ROS2 base image: `ros:humble-ros-base`

> Full Nav2/SLAM **runtime** evidence is collected during **local QA** (Docker +
> ROS2 required). CI verifies schemas, API, compose isolation, package/launch/
> config structure, and the pure-Python MiniLab logic. See ADR-009.

## Local QA commands (exact)

```bash
git checkout cursor/feat-phase-5-5-nav2-slam-minilab-5327   # PR branch
make install
make test
make lint
make compose-config        # core profile
make compose-nav-slam      # ros2-nav-slam profile

# Core stays independent
docker compose --profile core up --build -d

# Start the MiniLab (heavy image; first build pulls Nav2 + SLAM Toolbox)
docker compose --profile ros2-nav-slam up --build -d
docker compose --profile ros2-nav-slam ps
docker compose --profile ros2-nav-slam logs --tail=200

# Inspect ROS2 graph (adapt <service> = ros2_nav_slam)
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 node list
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic list
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic echo /scan
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic echo /odom
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic echo /axon/nav/status
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic echo /axon/slam/status

# Makefile shortcuts
make nav-slam-map-demo
make nav-slam-goal-demo
make nav-slam-blocked-demo
make nav-slam-status
make nav-slam-down
```

## Evidence items

### E1 — Core still works
```bash
docker compose --profile core up --build -d
curl -s http://localhost:8000/health | python3 -m json.tool   # twin_service.running=true
# Dashboard http://localhost:3000 loads; Digital Twin still updates.
```
Expected: core healthy, twin updates, Nav2/SLAM panel shows **offline** (profile down).

### E2 — `ros2-nav-slam` profile starts
```bash
docker compose --profile ros2-nav-slam up --build -d
docker compose --profile ros2-nav-slam ps
docker compose --profile ros2-nav-slam logs --tail=200
```
Expected: `ros2_nav_slam` running; logs show mini_world, nav_goal_runner,
slam_toolbox and Nav2 lifecycle activity (or documented limitations).

### E3 — ROS2 nodes and TF tree visible
```bash
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 node list
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 run tf2_tools view_frames
```
Expected: `mini_world_node`, `nav_goal_runner`, `slam_status_node`,
`axon_nav_slam_bridge`, plus `slam_toolbox` and Nav2 nodes where feasible. TF:
`map -> odom -> base_link`.

### E4 — `/scan` and `/odom` publish at usable rates
```bash
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic hz /scan
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic hz /odom
```
Expected: `/scan` ≥ 10 Hz, `/odom` ≥ 20 Hz (configurable via `SCAN_HZ`/`ODOM_HZ`).

### E5 — SLAM map/status publishes
```bash
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic echo /map --once
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic echo /axon/slam/status --once
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 service list
```
Expected: `/map` is `nav_msgs/OccupancyGrid`; `/axon/slam/status` non-empty;
`slam_toolbox` services visible.

### E6 — Navigation goal/status flow
```bash
make nav-slam-goal-demo
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic echo /axon/nav/status
```
Expected: status transitions through at least two states
(`idle → planning → navigating`, then `reached`). Not just `goal_sent`.

### E7 — Dashboard Nav2/SLAM panel
Expected: panel shows map/pose/goal/path/status when data flows; shows
**offline** gracefully when the profile is down; core dashboard never breaks.

### E8 — Blocked goal scenario
```bash
make nav-slam-blocked-demo
docker compose --profile ros2-nav-slam exec ros2_nav_slam ros2 topic echo /axon/nav/status
```
Expected: `blocked` (or `failed`) with a non-empty reason
(`Goal lies inside obstacle 'parallel_bars'.`). No fake success.

### E9 — Tests pass
```bash
make test
make lint
make compose-config
make compose-nav-slam
```
Expected: all tests pass (127 + Phase 5.5 additions); ruff clean; both profiles
validate.

### E10 — Scope / claims audit
Expected: no Fase 6, no federated learning, no RL, no hardware, no cloud
deployment, no medical claims, no patient data. Confirmed by
`test_no_forbidden_scope_terms_in_minilab_package` and
`test_scope_audit_minilab_docs_are_honest`.

## Local QA Run — 2026-06-07

- Branch: `cursor/feat-phase-5-5-nav2-slam-minilab-5327`
- Local worktree: `/Users/danny/project-5-pr9-qa`
- OS: macOS Darwin 25.5.0
- Docker: 29.5.2
- Docker Compose: v5.1.4
- Python: 3.12 via `.venv` (`python3` on host is 3.14.5)
- Node: not installed locally; dashboard is static and served by Python HTTP server.
- Browser: Cursor browser automation against `http://localhost:3000`
- Available RAM note: Docker reported 3.827 GiB limit.

| Command | Result | Notes |
|---|---|---|
| `make install` | PASS | Installed dev/edge-ai/agents/mlops deps in `.venv`. |
| `make test` | PASS | Final: `128 passed, 2 warnings`. |
| `make lint` | PASS | Ruff clean. |
| `make compose-config` | PASS | Core profile config valid. |
| `make compose-nav-slam` | PASS | `SCAN_HZ=12`, `ODOM_HZ=25`, `TF_HZ=25`; isolated service, no core dependency. |
| `python -m compileall services/ros2-nav-slam-minilab apps` | PASS | No syntax errors. |
| `docker compose --profile core up --build -d` | PASS | API/dashboard/edge-inference/mosquitto/redis/sensor-generators healthy. |
| `docker compose --profile ros2-nav-slam up --build -d` | PASS | Image built from `ros:humble-ros-base`; packages compiled; service stable. |
| `ros2 node list` / process audit | PASS | Processes: `mini_world_node`, `nav_goal_runner`, `slam_status_node`, `axon_nav_slam_bridge`, `slam_toolbox`, Nav2 servers. ROS2 CLI discovery can be partial; services/topics verified directly. |
| `ros2 run tf2_tools view_frames` | PASS | Generated `/ros2_ws/frames_2026-06-07_19.11.52.pdf` and `.gv`; `map -> odom -> base_link`. |
| `timeout 15 ros2 topic hz /scan` | PASS | Final observed averages around `11.998-12.000 Hz`. |
| `timeout 15 ros2 topic hz /odom` | PASS | Final observed averages around `24.897-24.920 Hz`. |
| `ros2 topic echo /scan --once` | PASS | `frame_id=base_link`; scan features: 128 parsed values, 50 distinct (`39.06%`), min `0.12`, max `0.8083` in sampled window. |
| `ros2 topic echo /odom --once` | PASS | `frame_id=odom`, `child_frame_id=base_link`. |
| `ros2 topic echo /map --once` | PASS | `nav_msgs/OccupancyGrid`, non-unknown data present (`HAS_NON_UNKNOWN=True`). |
| `ros2 topic echo /axon/slam/status --once` | PASS | `{"status":"stable","coverage_pct":48.35,"map_updates":62,"has_map":true}` during SLAM gate. |
| `ros2 service call /bt_navigator/get_state` | PASS | `current_state=id=3,label='active'`; same for `/planner_server` and `/controller_server`. |
| `make nav-slam-goal-demo` | PASS | `accepted=True`, status `navigating`, then `/axon/nav/status` transitioned to `reached`. |
| `make nav-slam-blocked-demo` | PASS | `accepted=False`, status `blocked`, reason `Goal lies inside obstacle 'parallel_bars'.` |
| Dashboard panel | PASS | Live panel shows SLAM stable / Nav blocked; stopped profile shows offline graceful. |
| WebSocket `/ws/v1/twin` | PASS | Browser received live `twin_state` frames. |
| WebSocket `/ws/v1/nav-slam` | PASS | Browser received live `nav_slam_state` frames with changing timestamp/status. |
| Resource audit | PASS | `ros2_nav_slam`: ~358 MiB RAM, no OOM/restarts observed; image ~3.27 GB and isolated. |

## Evidence E1-E10 Final

### E1 — Core still works
PASS.
Evidence: `docker compose --profile core ps`, `/health`, `/api/v1/twin/state`,
dashboard screenshot
`/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/phase-5-5-e1-core-twin-navslam-offline.png`,
and `/ws/v1/twin` browser frames.

### E2 — `ros2-nav-slam` profile starts
PASS.
Evidence: image build succeeded; `ros2_nav_slam` started; logs show
`mini_world_node started: scan=12.0Hz odom=25.0Hz tf=25.0Hz`, SLAM Toolbox
started, and `Managed nodes are active`.

### E3 — ROS2 nodes and TF tree visible
PASS.
Evidence: process list and ROS services show `mini_world_node`,
`nav_goal_runner`, `slam_status_node`, `axon_nav_slam_bridge`, `slam_toolbox`,
Nav2 controller/planner/BT/lifecycle processes. `view_frames` output:
`odom parent 'map'`, `base_link parent 'odom'`.

### E4 — `/scan` and `/odom` publish at usable rates
PASS.
Evidence: `/scan` final observed average around `12.0 Hz`; `/odom` final
observed average around `24.9 Hz`. `/scan` has geometric features with >30%
distinct sampled values.

### E5 — SLAM map/status publishes
PASS.
Evidence: `/map` occupancy grid contains non-unknown cells; `/axon/slam/status`
reported `stable`, coverage around `48.35%`, `map_updates=62` during the SLAM
gate. Later dashboard/backend showed stable coverage around `42-44%`.

### E6 — Navigation goal/status flow
PASS.
Evidence: `make nav-slam-goal-demo` returned `accepted=True`,
`status='navigating'`; `/axon/nav/status` emitted `navigating` then `reached`;
backend received goal/path/status.

### E7 — Dashboard Nav2/SLAM panel
PASS.
Evidence: live screenshot
`/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/phase-5-5-e7-dashboard-navslam-blocked-live.png`;
offline screenshot
`/var/folders/tz/y4rjqvzd5gnbc6tpxv80q_m80000gn/T/cursor/screenshots/phase-5-5-e7-dashboard-offline-graceful-after-stop.png`.

### E8 — Blocked goal scenario
PASS.
Evidence: `make nav-slam-blocked-demo` returned `accepted=False`,
`status='blocked'`, reason `Goal lies inside obstacle 'parallel_bars'.`;
backend reflected `bridge_status=degraded`, `nav_status=blocked`, non-empty
reason.

### E9 — Tests pass
PASS.
Evidence: final `make test` => `128 passed, 2 warnings`; final `make lint` =>
all checks passed; final `make compose-config` and `make compose-nav-slam` pass.

### E10 — Scope / claims audit
PASS.
Evidence: `rg` scope/claims audits found only roadmap future items,
placeholders, URLs, or explicit out-of-scope/no-claims disclaimers. No positive
Fase 6, federated learning, RL, hardware, cloud/Kubernetes, Gazebo/Isaac/
Omniverse dependency, real patient data, or medical claim was added.

## Local QA Final Verdict

PASS — PR #9 ready to merge after the final local QA fix commits are pushed.
The PR remains unmerged.

## Local QA Bugs / Fixes

---
BUG: Nav2/SLAM publish rates had no runtime margin
FOUND IN PHASE: Phase 6 — rates reales de `/scan` y `/odom`
ERROR:
  `timeout 15 ros2 topic hz /scan` reported final average `9.991` Hz.
  `timeout 15 ros2 topic hz /odom` reported final average `19.924` Hz.
ROOT CAUSE:
  `docker-compose.yml`, `.env.example`, `Dockerfile`, and `mini_world_node.py`
  used defaults exactly equal to the hard gates (`SCAN_HZ=10`, `ODOM_HZ=20`,
  `TF_HZ=20`). Timer jitter and ROS2 CLI measurement overhead can report just
  below the gate even when publishers are nominal.
FIX:
  Raised default runtime rates to `SCAN_HZ=12`, `ODOM_HZ=25`, `TF_HZ=25` while
  keeping the gates documented as `/scan >= 10 Hz` and `/odom >= 20 Hz`. Added a
  regression test that Compose defaults retain this margin.
VERIFIED BY:
  `make test` (`128 passed`), `make lint`, `make compose-nav-slam`,
  rebuilt `ros2_nav_slam`, then `timeout 15 ros2 topic hz /scan` (~12.0 Hz)
  and `timeout 15 ros2 topic hz /odom` (~24.9 Hz).
COMMIT:
  Pending final QA fix commit.
---

---
BUG: Reachable goal demo blocked from live patrol pose
FOUND IN PHASE: Phase 8 — Nav2 lifecycle y goal flow
ERROR:
  `make nav-slam-goal-demo` returned
  `SendNavGoal_Response(accepted=False, status='blocked', message="Direct path obstructed by 'treadmill' (no detour planner).", trace_id='qa-goal')`.
ROOT CAUSE:
  `nav_state_machine.py` only planned a straight-line segment. The documented
  goal `(5.0, 1.0)` is free, but from a live patrol pose near `(0.678, 0.6)` the
  direct segment crosses the `treadmill` obstacle, so a reachable demo was
  incorrectly rejected.
FIX:
  Added a deterministic visibility-graph detour planner over free room/obstacle
  waypoints and updated `nav_goal_runner.py` to command each planned waypoint
  instead of driving directly to the final goal.
VERIFIED BY:
  `make test` (`128 passed`), rebuilt `ros2_nav_slam`, `make nav-slam-goal-demo`
  returned `accepted=True`, `/axon/nav/status` emitted `navigating -> reached`,
  and backend status included goal/path/status.
COMMIT:
  Pending final QA fix commit.
---
