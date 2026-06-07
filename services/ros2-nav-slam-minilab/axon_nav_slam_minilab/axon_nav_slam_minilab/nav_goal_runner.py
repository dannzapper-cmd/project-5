#!/usr/bin/env python3
"""Navigation goal runner for the AXON Nav2 + SLAM MiniLab.

Drives the deterministic MiniLab navigation status flow and exposes the ROS2
services used for local QA. The robot pose authority is ``mini_world_node``;
this node observes ``/odom`` and commands a drive goal, while tracking the
honest status state machine (idle/planning/navigating/reached/blocked/failed).

Services:
  - /axon/nav_slam/send_goal     axon_nav_slam_interfaces/SendNavGoal
  - /axon/nav_slam/start_mapping std_srvs/Trigger
  - /axon/nav_slam/reset         std_srvs/Trigger

Publishes:
  - /axon/nav/status             std_msgs/String (JSON: status, reason, demo, pose, goal)
  - /axon/nav/goal               geometry_msgs/PoseStamped
  - /axon/nav/path               nav_msgs/Path
  - /axon/nav_slam/drive_goal    geometry_msgs/PoseStamped (command to mini_world_node)

This lightweight planner is deterministic and self-contained so demos produce
honest status flows regardless of full Nav2 lifecycle availability (see launch
file + ADR-009/ADR-010). It never reports a fake "reached"/"goal completed".
"""

from __future__ import annotations

import json
import math
import os

import rclpy
from axon_nav_slam_interfaces.srv import SendNavGoal
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger

from axon_nav_slam_minilab.nav_state_machine import NavStateMachine
from axon_nav_slam_minilab.world_model import WorldModel


def _yaw_to_quat_z_w(yaw: float) -> tuple[float, float]:
    return (math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class NavGoalRunner(Node):
    def __init__(self) -> None:
        super().__init__("nav_goal_runner")
        width = float(os.getenv("WORLD_WIDTH", "6.0"))
        height = float(os.getenv("WORLD_HEIGHT", "4.0"))
        self.world = WorldModel(width=width, height=height)
        self.sm = NavStateMachine(self.world)
        self.status_hz = float(os.getenv("NAV_STATUS_HZ", "2"))

        self._robot_xy = (width / 2.0, height / 2.0)
        self._mapping_active = False

        self.status_pub = self.create_publisher(String, "/axon/nav/status", 10)
        self.goal_pub = self.create_publisher(PoseStamped, "/axon/nav/goal", 10)
        self.path_pub = self.create_publisher(Path, "/axon/nav/path", 10)
        self.drive_pub = self.create_publisher(PoseStamped, "/axon/nav_slam/drive_goal", 10)

        self.create_subscription(Odometry, "/odom", self._on_odom, 20)

        self.create_service(SendNavGoal, "/axon/nav_slam/send_goal", self._on_send_goal)
        self.create_service(Trigger, "/axon/nav_slam/start_mapping", self._on_start_mapping)
        self.create_service(Trigger, "/axon/nav_slam/reset", self._on_reset)

        self.create_timer(1.0 / self.status_hz, self._tick)
        self.get_logger().info("nav_goal_runner started")

    def _on_odom(self, msg: Odometry) -> None:
        self._robot_xy = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def _on_send_goal(
        self, request: SendNavGoal.Request, response: SendNavGoal.Response
    ) -> SendNavGoal.Response:
        status = self.sm.plan(
            self._robot_xy,
            request.x,
            request.y,
            request.theta_deg,
            demo=request.demo or None,
        )
        response.accepted = status in ("planning", "navigating")
        response.status = status
        response.message = self.sm.reason or ""
        response.trace_id = request.trace_id or f"nav-{self.get_clock().now().nanoseconds}"

        self._publish_goal(request.x, request.y, request.theta_deg)
        self._publish_path()
        if response.accepted:
            self._publish_drive_goal(request.x, request.y)
        self._publish_status()
        self.get_logger().info(
            f"send_goal ({request.x:.2f},{request.y:.2f}) -> {status}: {self.sm.reason}"
        )
        return response

    def _on_start_mapping(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        self._mapping_active = True
        response.success = True
        response.message = (
            "Mapping active: mini_world_node patrol provides /scan + /odom + TF "
            "to SLAM Toolbox."
        )
        self.get_logger().info(response.message)
        return response

    def _on_reset(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        self.sm.reset()
        self._publish_status()
        response.success = True
        response.message = "MiniLab navigation state reset to idle."
        self.get_logger().info(response.message)
        return response

    def _publish_goal(self, x: float, y: float, theta_deg: float) -> None:
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        qz, qw = _yaw_to_quat_z_w(math.radians(theta_deg))
        msg.pose.orientation.z = qz
        msg.pose.orientation.w = qw
        self.goal_pub.publish(msg)

    def _publish_drive_goal(self, x: float, y: float) -> None:
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.orientation.w = 1.0
        self.drive_pub.publish(msg)

    def _publish_path(self) -> None:
        path = Path()
        path.header.stamp = self.get_clock().now().to_msg()
        path.header.frame_id = "map"
        for px, py in self.sm.path:
            ps = PoseStamped()
            ps.header.frame_id = "map"
            ps.pose.position.x = float(px)
            ps.pose.position.y = float(py)
            ps.pose.orientation.w = 1.0
            path.poses.append(ps)
        self.path_pub.publish(path)

    def _tick(self) -> None:
        rx, ry = self._robot_xy
        self.sm.update(rx, ry, dt=1.0 / self.status_hz)
        self._publish_status()

    def _publish_status(self) -> None:
        rx, ry = self._robot_xy
        payload = {
            "status": self.sm.status,
            "reason": self.sm.reason,
            "active_demo": self.sm.active_demo,
            "mapping_active": self._mapping_active,
            "robot_pose": [round(rx, 3), round(ry, 3)],
            "goal": list(self.sm.goal) if self.sm.goal else None,
            "path_waypoints": len(self.sm.path),
            "path_length_m": self.sm.path_length_m(),
        }
        msg = String()
        msg.data = json.dumps(payload)
        self.status_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NavGoalRunner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
