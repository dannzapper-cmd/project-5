# ADR-009: Nav2 + SLAM MiniLab Scope and Constraints (Fase 5.5)

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** AXON project owners
- **Extends:** ADR-005 (placeholder), ADR-008 (Phase 5 ROS2 thin adapter)

## Context

The AXON roadmap mandates an advanced ROS2 **Nav2 navigation + SLAM** MiniLab
(Phase 5.5) after the Phase 5 thin adapter. It must demonstrate that AXON can
run a robotics navigation/mapping layer **without physical hardware or a heavy
simulator**, and must remain fully isolated from the `core` daily-dev profile.

## Decision

1. **Isolated `ros2-nav-slam` Compose profile** with a single headless service
   `ros2_nav_slam`. It never starts with `core`; `core` does not depend on it;
   the MiniLab does not `depends_on` core (the bridge degrades gracefully when
   the API is offline).
2. **Same ROS2 distro as Phase 5** — `ros:humble-ros-base`. Real apt packages:
   `ros-humble-navigation2`, `ros-humble-nav2-bringup`, `ros-humble-slam-toolbox`,
   `ros-humble-tf2-ros`, `ros-humble-tf2-tools`.
3. **Two real ROS2 packages** in one colcon workspace:
   - `axon_nav_slam_interfaces` (`ament_cmake`, `SendNavGoal.srv`)
   - `axon_nav_slam_minilab` (`ament_python`: nodes + launch + config + maps)
4. **Real nodes** (`rclpy`): `mini_world_node`, `nav_goal_runner`,
   `slam_status_node`, `axon_nav_slam_bridge`.
5. **Real SLAM Toolbox** in `online_async` mapping mode against synthetic
   `/scan` + `/odom` + TF. **Real Nav2** navigation stack via
   `nav2_bringup/navigation_launch.py` (lifecycle managed, autostart). No AMCL —
   SLAM Toolbox owns `map->odom`.
6. **HTTP bridge to AXON** reusing the Phase 5 pattern: push state to
   `POST /api/v1/nav-slam/ingest`, poll operator commands from
   `GET /api/v1/nav-slam/pending-command`. No parallel/duplicate pipeline.
7. **Versioned schemas** in the existing schemas module
   (`apps/api/app/schemas/nav_slam.py`), broadcast on the shared WebSocket
   manager channel `nav-slam` (`/ws/v1/nav-slam`), mirroring the twin path.

## TF tree (exact)

```
map --(slam_toolbox)--> odom --(mini_world_node)--> base_link
```

`LaserScan.frame_id=base_link`; `Odometry.frame_id=odom child=base_link`.

## Lightweight deterministic planner vs full Nav2

`nav_goal_runner` runs a small, deterministic, rclpy-free state machine
(`nav_state_machine.py`) that validates goals and emits honest status
transitions (`idle → planning → navigating → reached | blocked | failed`). This
guarantees reproducible, **non-faked** AXON status flows and is unit-tested in
CI. The full Nav2 stack is launched in parallel and is the "real" navigation
runtime validated by local QA. The MiniLab never reports a fake `reached`.

## What CI verifies vs local QA

- **CI (no Docker/ROS2):** schemas, backend API, compose profile isolation,
  ROS2 package structure, SLAM/launch config correctness, and the pure-Python
  world model + nav state machine logic.
- **Local QA (Docker + ROS2):** image build, node startup, topic rates, TF
  tree, SLAM `/map`, Nav2 lifecycle, goal/blocked flows, dashboard panel.

Because Cursor Web has no Docker/ROS2 runtime, full Nav2/SLAM lifecycle is
**pending local QA** (B7 fallback by environment). All package/launch/config
code is real and runnable — not placeholders.

## Constraints (non-negotiable)

- No Gazebo / Isaac / Omniverse / RViz as required dependencies. Headless only.
- No physical robot, no patient data, no medical claims, no clinical autonomy.
- No Kubernetes, no cloud deployment, no Fase 6 (federated learning / RL).
- `core` profile behavior is unchanged.

## Consequences

- `docker compose --profile ros2-nav-slam up --build` starts a real ROS2
  Nav2 + SLAM MiniLab verifiable via `ros2 node/topic list` and `ros2 topic hz`.
- Phase 5 remains intact and extended, not replaced.
