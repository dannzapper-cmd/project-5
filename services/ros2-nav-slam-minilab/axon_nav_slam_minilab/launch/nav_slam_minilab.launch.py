"""AXON Phase 5.5 — headless Nav2 + SLAM MiniLab launch.

Startup ordering (B4: TF must exist before consumers start):
  t+0s   mini_world_node            (publishes /scan, /odom, TF odom->base_link)
  t+0s   nav_goal_runner            (services + AXON nav status)
  t+0s   slam_status_node           (mirrors /map -> /axon/slam/status)
  t+0s   axon_nav_slam_bridge       (HTTP bridge to AXON backend)
  t+3s   slam_toolbox online_async  (owns map->odom while mapping)
  t+8s   nav2 navigation_launch     (lifecycle managed by nav2_bringup, autostart)

Lifecycle strategy (B6 Option A): nav2_bringup/navigation_launch.py provides the
lifecycle_manager_navigation with autostart=true managing controller_server,
planner_server, behavior_server, bt_navigator and smoother_server. No AMCL
(SLAM Toolbox supplies map->odom). No RViz, no Gazebo, no GUI.

Toggle heavy stacks with launch args: enable_slam:=false, enable_nav2:=false.
"""

from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("axon_nav_slam_minilab")
    slam_params = os.path.join(pkg_share, "config", "slam_toolbox_params.yaml")
    nav2_params = os.path.join(pkg_share, "config", "nav2_params.yaml")

    enable_slam = LaunchConfiguration("enable_slam")
    enable_nav2 = LaunchConfiguration("enable_nav2")

    declare_enable_slam = DeclareLaunchArgument(
        "enable_slam", default_value="true", description="Launch SLAM Toolbox online_async"
    )
    declare_enable_nav2 = DeclareLaunchArgument(
        "enable_nav2", default_value="true", description="Launch Nav2 navigation stack"
    )

    mini_world = Node(
        package="axon_nav_slam_minilab",
        executable="mini_world_node",
        name="mini_world_node",
        output="screen",
        # SLAM Toolbox owns map->odom in this launch; mini_world only emits
        # odom->base_link to avoid a conflicting transform publisher.
        additional_env={"PUBLISH_STATIC_MAP_ODOM": "false"},
    )
    nav_goal_runner = Node(
        package="axon_nav_slam_minilab",
        executable="nav_goal_runner",
        name="nav_goal_runner",
        output="screen",
    )
    slam_status = Node(
        package="axon_nav_slam_minilab",
        executable="slam_status_node",
        name="slam_status_node",
        output="screen",
    )
    axon_bridge = Node(
        package="axon_nav_slam_minilab",
        executable="axon_nav_slam_bridge",
        name="axon_nav_slam_bridge",
        output="screen",
    )

    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("slam_toolbox"),
                "launch",
                "online_async_launch.py",
            )
        ),
        launch_arguments={
            "slam_params_file": slam_params,
            "use_sim_time": "false",
        }.items(),
        condition=IfCondition(enable_slam),
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("nav2_bringup"),
                "launch",
                "navigation_launch.py",
            )
        ),
        launch_arguments={
            "params_file": nav2_params,
            "use_sim_time": "false",
            "autostart": "true",
        }.items(),
        condition=IfCondition(enable_nav2),
    )

    return LaunchDescription(
        [
            declare_enable_slam,
            declare_enable_nav2,
            mini_world,
            nav_goal_runner,
            slam_status,
            axon_bridge,
            TimerAction(period=3.0, actions=[slam_launch]),
            TimerAction(
                period=8.0,
                actions=[nav2_launch],
                condition=IfCondition(PythonExpression(["'", enable_nav2, "' == 'true'"])),
            ),
        ]
    )
