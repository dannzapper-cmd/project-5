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

## Local QA Run — (to be filled by Cursor local)

| Command | Result | Notes |
|---|---|---|
| `make install` | | |
| `make test` | | |
| `make lint` | | |
| `make compose-config` | | |
| `make compose-nav-slam` | | |
| `docker compose --profile core up --build -d` | | |
| `docker compose --profile ros2-nav-slam up --build -d` | | |
| `ros2 node list` | | |
| `ros2 run tf2_tools view_frames` | | |
| `ros2 topic hz /scan` | | |
| `ros2 topic hz /odom` | | |
| `ros2 topic echo /map --once` | | |
| `make nav-slam-goal-demo` | | |
| `make nav-slam-blocked-demo` | | |
| Dashboard panel | | |
