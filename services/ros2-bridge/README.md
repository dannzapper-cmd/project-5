# AXON ROS2 Thin Adapter (Phase 5)

Real `rclpy` bridge isolated in the `ros2` Docker Compose profile.

## Behavior

- Polls `GET /api/v1/twin/state` from AXON API
- Publishes JSON twin snapshots on `/axon/twin/state` (`std_msgs/String`)
- Publishes `/axon/bridge/heartbeat`
- Service `/axon/command` (`axon_ros2_bridge/srv/TwinCommand`) forwards to `POST /api/v1/twin/command`
- Posts heartbeat to `POST /api/v1/twin/ros2-heartbeat`

## Run

Requires `core` profile (API + Redis + telemetry):

```bash
docker compose --profile core --profile ros2 up --build
make ros2-up   # equivalent shortcut
```

## Verify

```bash
docker compose --profile ros2 exec ros2_bridge ros2 topic list
docker compose --profile ros2 exec ros2_bridge ros2 topic echo /axon/twin/state
docker compose --profile ros2 exec ros2_bridge ros2 service list
docker compose --profile ros2 exec ros2_bridge ros2 service call /axon/command axon_ros2_bridge/srv/TwinCommand "{command: 'pause', requested_by: 'ros2-qa', reason: 'demo', assist_mode: ''}"
```

## Not in Phase 5

Nav2, SLAM, Gazebo, hardware drivers, navigation actions (Phase 5.5+).
