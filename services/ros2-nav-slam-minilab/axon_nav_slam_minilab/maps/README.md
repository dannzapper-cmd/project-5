# MiniLab maps

SLAM Toolbox writes generated maps here at runtime (local QA). The map is
produced live from synthetic `/scan` + `/odom` + TF as the robot patrols the
simulated rehab lab — it is **not** committed as a pre-baked artifact, so the
MiniLab demonstrates real online mapping rather than replaying a fixed map.

Save a snapshot during local QA with:

```bash
docker compose --profile ros2-nav-slam exec ros2_nav_slam \
  bash -lc "source /opt/ros/humble/setup.bash && \
            ros2 run nav2_map_server map_saver_cli -f /ros2_ws/src/axon_nav_slam_minilab/maps/minilab_map"
```

This produces `minilab_map.pgm` + `minilab_map.yaml` (git-ignored).
