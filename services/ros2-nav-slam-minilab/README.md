# AXON ROS2 Nav2 + SLAM MiniLab (Phase 5.5)

Headless, reproducible ROS2 **Nav2 navigation + SLAM** lab in the isolated
`ros2-nav-slam` Docker Compose profile. Extends the Phase 5 ROS2 thin adapter
(`services/ros2-bridge`) without replacing it.

> Simulated robotics navigation/mapping lab. **No physical robot. No clinical
> autonomy. No medical claims. No patient data.** Synthetic signals only.

## What it is

Two ROS2 packages built in one colcon workspace on `ros:humble-ros-base`:

| Package | Build type | Purpose |
|---------|-----------|---------|
| `axon_nav_slam_interfaces` | `ament_cmake` | `SendNavGoal.srv` |
| `axon_nav_slam_minilab` | `ament_python` | nodes, launch, config, maps |

Real apt packages installed: `ros-humble-navigation2`, `ros-humble-nav2-bringup`,
`ros-humble-slam-toolbox`, `ros-humble-tf2-ros`, `ros-humble-tf2-tools`.

## Nodes

| Node | Role |
|------|------|
| `mini_world_node` | Synthetic rehab lab: `/scan`, `/odom`, TF (`odom->base_link`), heartbeat |
| `nav_goal_runner` | Goal services + deterministic nav status flow (`/axon/nav/*`) |
| `slam_status_node` | Reads `/map`, publishes coverage metrics (`/axon/slam/status`) |
| `axon_nav_slam_bridge` | HTTP bridge to AXON backend (ingest + command poll) |

Plus real `slam_toolbox` (online_async) and `nav2_bringup` navigation stack
launched by `launch/nav_slam_minilab.launch.py`.

## TF tree

```
map --(slam_toolbox)--> odom --(mini_world_node)--> base_link
```

- `LaserScan.header.frame_id = base_link`
- `Odometry.header.frame_id = odom`, `child_frame_id = base_link`

`mini_world_node` can also publish a static `map->odom` anchor standalone
(`PUBLISH_STATIC_MAP_ODOM=true`, the default for `ros2 run`); the launch file
sets it to `false` so SLAM Toolbox owns `map->odom`.

## Run

```bash
docker compose --profile core up --build -d          # AXON backend (for bridge)
docker compose --profile ros2-nav-slam up --build -d  # MiniLab
make nav-slam-status
```

See the repo `README.md` Phase 5.5 section, `docs/evidence/phase-5-5-nav2-slam-minilab.md`,
and ADR-009 / ADR-010 for full local QA instructions, limitations, and scope.

## Pure-Python logic (CI-testable)

`world_model.py` (geometry/raycasting/patrol) and `nav_state_machine.py`
(goal validation, planning, status transitions) contain **no ROS imports** and
are unit tested in normal CI (`tests/test_phase5_5_nav_slam.py`). Full ROS2
runtime (SLAM/Nav2 lifecycle) is verified by **local QA** — see ADR-009.
