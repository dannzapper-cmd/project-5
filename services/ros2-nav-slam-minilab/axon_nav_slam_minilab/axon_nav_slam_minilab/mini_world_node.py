#!/usr/bin/env python3
"""Headless synthetic mini-world node for the AXON Nav2 + SLAM MiniLab.

Publishes deterministic synthetic sensor + TF data so SLAM Toolbox (and, where
feasible, Nav2) have real inputs to consume — no Gazebo, no RViz, no GUI.

Publishes:
  - /scan                       sensor_msgs/LaserScan   (>= SCAN_HZ, default 10 Hz)
  - /odom                       nav_msgs/Odometry       (>= ODOM_HZ, default 20 Hz)
  - /tf  (odom -> base_link)    tf2_msgs/TFMessage      (>= TF_HZ, default 20 Hz)
  - /tf_static (map -> odom)    tf2_msgs/TFMessage      (latched, optional)
  - /axon/nav_slam/heartbeat    std_msgs/String         (NAV_SLAM_HEARTBEAT_HZ, default 1 Hz)

Subscribes:
  - /axon/nav_slam/drive_goal   geometry_msgs/PoseStamped  (drive toward goal; else patrol)

Frames (exact, per Nav2 TF requirements):
  - map frame:        "map"
  - odom frame:       "odom"
  - robot base frame: "base_link"
  - LaserScan header.frame_id = base_link
  - Odometry header.frame_id  = odom, child_frame_id = base_link

NOTE on map->odom: when SLAM Toolbox is running it owns the map->odom transform.
Set PUBLISH_STATIC_MAP_ODOM=false in that case (the launch file does this) so this
node only publishes odom->base_link. Standalone (no SLAM) it can publish a static
map->odom anchor so the full map->odom->base_link tree exists for verification.
"""

from __future__ import annotations

import math
import os

import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

from axon_nav_slam_minilab.world_model import PatrolTrajectory, WorldModel


def _yaw_to_quat(yaw: float) -> tuple[float, float, float, float]:
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class MiniWorldNode(Node):
    def __init__(self) -> None:
        super().__init__("mini_world_node")
        self.scan_hz = float(os.getenv("SCAN_HZ", "10"))
        self.odom_hz = float(os.getenv("ODOM_HZ", "20"))
        self.tf_hz = float(os.getenv("TF_HZ", "20"))
        self.heartbeat_hz = float(os.getenv("NAV_SLAM_HEARTBEAT_HZ", "1"))
        self.scan_readings = int(os.getenv("SCAN_READINGS", "180"))
        self.publish_static_map_odom = (
            os.getenv("PUBLISH_STATIC_MAP_ODOM", "true").lower() == "true"
        )

        width = float(os.getenv("WORLD_WIDTH", "6.0"))
        height = float(os.getenv("WORLD_HEIGHT", "4.0"))
        self.world = WorldModel(width=width, height=height)
        self.patrol = PatrolTrajectory(self.world)

        self.angle_min = -math.pi
        self.angle_max = math.pi

        self.scan_pub = self.create_publisher(LaserScan, "/scan", 10)
        self.odom_pub = self.create_publisher(Odometry, "/odom", 20)
        self.heartbeat_pub = self.create_publisher(String, "/axon/nav_slam/heartbeat", 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.static_broadcaster = StaticTransformBroadcaster(self)

        self.create_subscription(
            PoseStamped, "/axon/nav_slam/drive_goal", self._on_drive_goal, 10
        )

        self._elapsed = 0.0
        self._drive_goal: tuple[float, float] | None = None
        # Start at first patrol waypoint.
        self._pose = self.patrol.pose_at(0.0)

        if self.publish_static_map_odom:
            self._publish_static_map_odom()

        self.create_timer(1.0 / self.scan_hz, self._publish_scan)
        self.create_timer(1.0 / self.odom_hz, self._publish_odom)
        self.create_timer(1.0 / self.tf_hz, self._publish_tf)
        self.create_timer(1.0 / max(self.heartbeat_hz, 0.1), self._publish_heartbeat)
        self._motion_dt = 1.0 / self.odom_hz
        self.create_timer(self._motion_dt, self._advance_motion)

        self.get_logger().info(
            f"mini_world_node started: scan={self.scan_hz}Hz odom={self.odom_hz}Hz "
            f"tf={self.tf_hz}Hz world={width}x{height}m "
            f"static_map_odom={self.publish_static_map_odom}"
        )

    def _publish_static_map_odom(self) -> None:
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = "map"
        t.child_frame_id = "odom"
        t.transform.rotation.w = 1.0
        self.static_broadcaster.sendTransform(t)
        self.get_logger().info("Published static map->odom anchor")

    def _on_drive_goal(self, msg: PoseStamped) -> None:
        self._drive_goal = (msg.pose.position.x, msg.pose.position.y)
        self.get_logger().info(f"drive_goal set: {self._drive_goal}")

    def _advance_motion(self) -> None:
        if self._drive_goal is not None:
            gx, gy = self._drive_goal
            x, y, _ = self._pose
            dx, dy = gx - x, gy - y
            dist = math.hypot(dx, dy)
            step = self.patrol.speed_mps * self._motion_dt
            if dist <= step or dist < 1e-3:
                self._pose = (gx, gy, math.atan2(dy, dx) if dist > 1e-6 else self._pose[2])
                self._drive_goal = None
            else:
                heading = math.atan2(dy, dx)
                self._pose = (x + step * dx / dist, y + step * dy / dist, heading)
        else:
            self._elapsed += self._motion_dt
            self._pose = self.patrol.pose_at(self._elapsed)

    def _publish_scan(self) -> None:
        x, y, heading = self._pose
        ranges = self.world.compute_scan(
            x, y, heading, self.scan_readings, self.angle_min, self.angle_max
        )
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.angle_min = self.angle_min
        msg.angle_max = self.angle_max
        msg.angle_increment = (self.angle_max - self.angle_min) / (self.scan_readings - 1)
        msg.range_min = self.world.range_min
        msg.range_max = self.world.range_max
        msg.scan_time = 1.0 / self.scan_hz
        msg.time_increment = 0.0
        msg.ranges = [float(r) for r in ranges]
        self.scan_pub.publish(msg)

    def _publish_odom(self) -> None:
        x, y, yaw = self._pose
        qx, qy, qz, qw = _yaw_to_quat(yaw)
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "odom"
        msg.child_frame_id = "base_link"
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        self.odom_pub.publish(msg)

    def _publish_tf(self) -> None:
        x, y, yaw = self._pose
        qx, qy, qz, qw = _yaw_to_quat(yaw)
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = "odom"
        t.child_frame_id = "base_link"
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.rotation.x = qx
        t.transform.rotation.y = qy
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(t)

    def _publish_heartbeat(self) -> None:
        x, y, yaw = self._pose
        msg = String()
        msg.data = (
            '{"node": "mini_world_node", "pose": '
            f"[{x:.3f}, {y:.3f}, {yaw:.3f}], "
            f'"mode": "{"goto" if self._drive_goal else "patrol"}"}}'
        )
        self.heartbeat_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MiniWorldNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
