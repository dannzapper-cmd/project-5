#!/usr/bin/env python3
"""SLAM status bridge for the AXON Nav2 + SLAM MiniLab.

Subscribes to the occupancy grid produced by SLAM Toolbox and publishes
AXON-friendly map coverage / update metrics.

Subscribes:
  - /map                 nav_msgs/OccupancyGrid (from slam_toolbox)

Publishes:
  - /axon/slam/status    std_msgs/String (JSON: status, coverage_pct, cells, updates)
  - /axon/slam/map       std_msgs/String (JSON summary mirror of /map metadata)

If SLAM Toolbox is not yet publishing /map (e.g. still initializing or pending
local QA), the node reports an honest "inactive"/"mapping" status rather than a
fake completed map.
"""

from __future__ import annotations

import json

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from std_msgs.msg import String


class SlamStatusNode(Node):
    def __init__(self) -> None:
        super().__init__("slam_status_node")
        self._map_updates = 0
        self._last_coverage = 0.0
        self._has_map = False

        self.status_pub = self.create_publisher(String, "/axon/slam/status", 10)
        self.map_summary_pub = self.create_publisher(String, "/axon/slam/map", 10)
        self.create_subscription(OccupancyGrid, "/map", self._on_map, 10)
        self.create_timer(1.0, self._publish_status)
        self.get_logger().info("slam_status_node started; waiting for /map")

    def _on_map(self, msg: OccupancyGrid) -> None:
        self._has_map = True
        self._map_updates += 1
        width = msg.info.width
        height = msg.info.height
        total = max(1, width * height)
        known = sum(1 for v in msg.data if v >= 0)
        self._last_coverage = round(100.0 * known / total, 2)
        summary = {
            "resolution_m": round(msg.info.resolution, 4),
            "width_cells": width,
            "height_cells": height,
            "known_cells": known,
            "total_cells": total,
            "coverage_pct": self._last_coverage,
            "map_updates": self._map_updates,
        }
        out = String()
        out.data = json.dumps(summary)
        self.map_summary_pub.publish(out)

    def _publish_status(self) -> None:
        if not self._has_map:
            status = "inactive"
        elif self._last_coverage <= 0.0:
            status = "mapping"
        elif self._last_coverage < 30.0:
            status = "mapping"
        else:
            status = "stable"
        payload = {
            "status": status,
            "coverage_pct": self._last_coverage,
            "map_updates": self._map_updates,
            "has_map": self._has_map,
        }
        msg = String()
        msg.data = json.dumps(payload)
        self.status_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SlamStatusNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
