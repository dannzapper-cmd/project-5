"""Launch AXON ROS2 twin bridge node."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="axon_ros2_bridge",
                executable="twin_bridge_node",
                name="axon_twin_bridge",
                output="screen",
                parameters=[],
            ),
        ]
    )
