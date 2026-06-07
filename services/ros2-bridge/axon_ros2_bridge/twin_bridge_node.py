#!/usr/bin/env python3
"""ROS2 bridge node: mirror AXON digital twin state and forward commands."""

from __future__ import annotations

import json
import os

import rclpy
import requests
from axon_ros2_bridge.srv import TwinCommand
from rclpy.node import Node
from std_msgs.msg import String


class TwinBridgeNode(Node):
    """Publish /axon/twin/state and expose /axon/command service."""

    def __init__(self) -> None:
        super().__init__("axon_twin_bridge")
        self.api_base = os.getenv("AXON_API_BASE", "http://api:8000")
        self.poll_hz = float(os.getenv("ROS2_TWIN_POLL_HZ", "2"))
        self.state_pub = self.create_publisher(String, "/axon/twin/state", 10)
        self.heartbeat_pub = self.create_publisher(String, "/axon/bridge/heartbeat", 10)
        self.timer = self.create_timer(1.0 / self.poll_hz, self._poll_twin_state)
        self.srv = self.create_service(TwinCommand, "/axon/command", self._handle_command)
        self.get_logger().info("AXON twin bridge started — API %s", self.api_base)

    def _poll_twin_state(self) -> None:
        try:
            resp = requests.get(f"{self.api_base}/api/v1/twin/state", timeout=3)
            resp.raise_for_status()
            payload = resp.json()
            msg = String()
            msg.data = json.dumps(payload)
            self.state_pub.publish(msg)
            requests.post(
                f"{self.api_base}/api/v1/twin/ros2-heartbeat",
                params={"command_status": "publishing"},
                timeout=2,
            )
            hb = String()
            hb.data = json.dumps(
                {"status": "connected", "timestamp": payload.get("timestamp")}
            )
            self.heartbeat_pub.publish(hb)
        except Exception as exc:
            self.get_logger().warning("Twin poll failed: %s", exc)

    def _handle_command(
        self, request: TwinCommand.Request, response: TwinCommand.Response
    ) -> TwinCommand.Response:
        try:
            body = {
                "schema_version": "v1",
                "command": request.command,
                "requested_by": request.requested_by or "ros2_bridge",
                "reason": request.reason or None,
            }
            if request.assist_mode:
                body["assist_mode"] = request.assist_mode
            resp = requests.post(
                f"{self.api_base}/api/v1/twin/command",
                json=body,
                timeout=5,
            )
            data = resp.json()
            response.success = data.get("status") in ("accepted", "pending_hitl")
            response.status = data.get("status", "rejected")
            response.message = data.get("reason", "")
            response.trace_id = data.get("trace_id", "")
            requests.post(
                f"{self.api_base}/api/v1/twin/ros2-heartbeat",
                params={"command_status": response.status},
                timeout=2,
            )
        except Exception as exc:
            response.success = False
            response.status = "rejected"
            response.message = str(exc)
            response.trace_id = ""
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TwinBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
