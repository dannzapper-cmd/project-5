#!/usr/bin/env python3
# AXON Phase 5.5 Integration Inventory
# Extends Phase 5 ROS2 bridge:
#   - service: ros2_bridge
#   - path: services/ros2-bridge/
#   - ROS2 package: axon_ros2_bridge (services/ros2-bridge/axon_ros2_bridge/twin_bridge_node.py)
#   - ROS2 image: ros:humble-ros-base
# Digital twin schema:
#   - DigitalTwinStateV1 import path: apps/api/app/schemas/twin.py
# Phase 5.5 schemas (same module family):
#   - apps/api/app/schemas/nav_slam.py
#     (NavSlamStateV1, NavGoalV1, NavPathV1, SlamMapStatusV1,
#      NavSlamCommandRequestV1, NavSlamCommandResponseV1, NavSlamIngestV1)
# Backend integration (mirrors Phase 5 HTTP-bridge pattern, not a parallel system):
#   - POST /api/v1/nav-slam/ingest           push live MiniLab state
#   - GET  /api/v1/nav-slam/pending-command  poll operator commands
# Existing WebSocket pattern reused:
#   - /ws/v1/twin (twin)  ->  /ws/v1/nav-slam (nav-slam) broadcast channel
# Existing evidence docs:
#   - docs/evidence/
# Latest ADR before this phase: ADR-008 (this phase adds ADR-009, ADR-010)
"""AXON Nav2 + SLAM MiniLab bridge: ROS2 topics <-> AXON FastAPI backend.

Mirrors the Phase 5 thin-adapter pattern: this node calls the existing AXON
FastAPI endpoints over HTTP rather than building a parallel pipeline. It pushes
the live MiniLab navigation/mapping state into AXON and forwards operator
commands queued in AXON to the MiniLab ROS2 services.

Subscribes:
  - /axon/nav/status          std_msgs/String
  - /axon/slam/status         std_msgs/String
  - /axon/nav/path            nav_msgs/Path
  - /odom                     nav_msgs/Odometry
  - /axon/nav_slam/heartbeat  std_msgs/String

Calls (clients):
  - /axon/nav_slam/send_goal     axon_nav_slam_interfaces/SendNavGoal
  - /axon/nav_slam/start_mapping std_srvs/Trigger
  - /axon/nav_slam/reset         std_srvs/Trigger
"""

from __future__ import annotations

import json
import math
import os

import rclpy
import requests
from axon_nav_slam_interfaces.srv import SendNavGoal
from nav_msgs.msg import Odometry, Path
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger


class AxonNavSlamBridge(Node):
    def __init__(self) -> None:
        super().__init__("axon_nav_slam_bridge")
        self.api_base = os.getenv("AXON_API_BASE", "http://api:8000")
        self.ingest_hz = float(os.getenv("NAV_SLAM_INGEST_HZ", "2"))
        self.poll_hz = float(os.getenv("NAV_SLAM_COMMAND_POLL_HZ", "2"))

        self._nav_status: dict = {}
        self._slam_status: dict = {}
        self._path_waypoints: list[tuple[float, float]] = []
        self._path_length = 0.0
        self._robot_pose = (0.0, 0.0, 0.0)
        self._last_seq = 0

        self.create_subscription(String, "/axon/nav/status", self._on_nav_status, 10)
        self.create_subscription(String, "/axon/slam/status", self._on_slam_status, 10)
        self.create_subscription(Path, "/axon/nav/path", self._on_path, 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 20)

        self.send_goal_client = self.create_client(SendNavGoal, "/axon/nav_slam/send_goal")
        self.start_mapping_client = self.create_client(Trigger, "/axon/nav_slam/start_mapping")
        self.reset_client = self.create_client(Trigger, "/axon/nav_slam/reset")

        self.create_timer(1.0 / self.ingest_hz, self._push_ingest)
        self.create_timer(1.0 / self.poll_hz, self._poll_commands)
        self.get_logger().info(f"axon_nav_slam_bridge started - API {self.api_base}")

    def _on_nav_status(self, msg: String) -> None:
        try:
            self._nav_status = json.loads(msg.data)
        except json.JSONDecodeError:
            pass

    def _on_slam_status(self, msg: String) -> None:
        try:
            self._slam_status = json.loads(msg.data)
        except json.JSONDecodeError:
            pass

    def _on_path(self, msg: Path) -> None:
        wps = [(p.pose.position.x, p.pose.position.y) for p in msg.poses]
        length = 0.0
        for i in range(1, len(wps)):
            length += math.hypot(wps[i][0] - wps[i - 1][0], wps[i][1] - wps[i - 1][1])
        self._path_waypoints = wps
        self._path_length = round(length, 4)

    def _on_odom(self, msg: Odometry) -> None:
        q = msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self._robot_pose = (
            round(msg.pose.pose.position.x, 3),
            round(msg.pose.pose.position.y, 3),
            round(yaw, 3),
        )

    def _build_ingest(self) -> dict:
        nav = self._nav_status
        slam = self._slam_status
        goal = nav.get("goal")
        payload: dict = {
            "schema_version": "v1",
            "nav_status": nav.get("status", "idle"),
            "nav_status_reason": nav.get("reason"),
            "active_demo": nav.get("active_demo"),
            "robot_pose": list(self._robot_pose),
            "path": {
                "schema_version": "v1",
                "frame_id": "map",
                "waypoints": [list(w) for w in self._path_waypoints],
                "length_m": self._path_length,
                "waypoint_count": len(self._path_waypoints),
            },
        }
        if goal:
            payload["goal"] = {
                "schema_version": "v1",
                "x": float(goal[0]),
                "y": float(goal[1]),
                "theta_deg": float(goal[2]) if len(goal) > 2 else 0.0,
                "frame_id": "map",
            }
        if slam:
            payload["slam"] = {
                "schema_version": "v1",
                "status": slam.get("status", "inactive"),
                "coverage_pct": float(slam.get("coverage_pct", 0.0)),
                "map_updates": int(slam.get("map_updates", 0)),
            }
        return payload

    def _push_ingest(self) -> None:
        try:
            requests.post(
                f"{self.api_base}/api/v1/nav-slam/ingest",
                json=self._build_ingest(),
                timeout=2,
            )
        except requests.RequestException as exc:
            self.get_logger().debug(f"ingest push failed: {exc}")

    def _poll_commands(self) -> None:
        try:
            resp = requests.get(
                f"{self.api_base}/api/v1/nav-slam/pending-command",
                params={"after_seq": self._last_seq},
                timeout=2,
            )
            resp.raise_for_status()
            cmd = resp.json()
        except requests.RequestException as exc:
            self.get_logger().debug(f"command poll failed: {exc}")
            return
        if not cmd or cmd.get("command") is None:
            return
        self._last_seq = int(cmd.get("seq", self._last_seq))
        self._dispatch_command(cmd)

    def _dispatch_command(self, cmd: dict) -> None:
        name = cmd.get("command")
        if name == "send_goal" and cmd.get("goal"):
            goal = cmd["goal"]
            if self.send_goal_client.service_is_ready():
                req = SendNavGoal.Request()
                req.x = float(goal.get("x", 0.0))
                req.y = float(goal.get("y", 0.0))
                req.theta_deg = float(goal.get("theta_deg", 0.0))
                req.demo = cmd.get("demo") or ""
                req.trace_id = cmd.get("trace_id") or ""
                self.send_goal_client.call_async(req)
                self.get_logger().info(f"Forwarded goal to MiniLab: {goal}")
        elif name == "start_mapping" and self.start_mapping_client.service_is_ready():
            self.start_mapping_client.call_async(Trigger.Request())
        elif name == "reset" and self.reset_client.service_is_ready():
            self.reset_client.call_async(Trigger.Request())


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AxonNavSlamBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
