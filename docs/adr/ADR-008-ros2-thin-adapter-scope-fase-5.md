# ADR-008: ROS2 Thin Adapter Scope in Fase 5

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** AXON project owners
- **Also referenced as:** ADR-006 (Phase 5 addendum) — ROS2 Thin Adapter Scope

## Context

AXON needs robotics interoperability for portfolio credibility, but full ROS2 desktop installs and Nav2/SLAM stacks must not become default dependencies. Phase 5.5 is explicitly reserved for Nav2 + SLAM MiniLab.

## Decision

1. **Isolated `ros2` Compose profile** — `ros2_bridge` service uses official `ros:humble-ros-base` image; never starts with `core`.
2. **Real rclpy node** — `axon_ros2_bridge/twin_bridge_node.py`:
   - Publishes `std_msgs/String` JSON on `/axon/twin/state` (polled from AXON API)
   - Publishes `/axon/bridge/heartbeat`
   - Exposes `/axon/command` service (`TwinCommand.srv`) forwarding to `POST /api/v1/twin/command`
3. **HTTP bridge to AXON** — ROS2 container calls existing FastAPI endpoints; no duplicate MQTT/Redis shadow pipeline.
4. **Defer to Phase 5.5** — Nav2, SLAM, `/axon/nav/execute_rehab_route`, full sensor topic mirroring from ROS2 → MQTT.

## Trade-offs

| Choice | Benefit | Cost |
|--------|---------|------|
| Thin adapter vs full stack | Runnable demo, smaller image | Limited robotics semantics |
| Poll API vs native Redis in ROS2 | Reuses twin contract | Slight latency vs in-process |
| Custom srv + String topic | Demonstrates service + topic patterns | Not full `robot_state` ROS message types |

## Consequences

- `docker compose --profile ros2 up` starts a **real** ROS2 node verifiable via `ros2 topic echo /axon/twin/state`.
- CI validates package structure statically; full ROS2 run is local QA.
- Phase 5.5 extends bridge with Nav2/SLAM without rewriting twin schema.

## Verification commands

```bash
docker compose --profile ros2 up --build
docker compose --profile ros2 exec ros2_bridge ros2 topic list
docker compose --profile ros2 exec ros2_bridge ros2 topic echo /axon/twin/state
docker compose --profile ros2 exec ros2_bridge ros2 service list
docker compose --profile ros2 exec ros2_bridge ros2 service call /axon/command axon_ros2_bridge/srv/TwinCommand "{command: 'pause', requested_by: 'qa', reason: 'test', assist_mode: ''}"
```

## Out of scope (Phase 5)

- Nav2, SLAM, Gazebo, navigation actions
- Hardware drivers
- Kubernetes / cloud deployment
