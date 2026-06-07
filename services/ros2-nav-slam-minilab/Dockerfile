# AXON Phase 5.5 — ROS2 Nav2 + SLAM MiniLab (headless).
# Uses the same ROS2 distro/base image family as Phase 5 (ros:humble-ros-base).
# No Gazebo, no Isaac, no Omniverse, no RViz, no GUI.
FROM ros:humble-ros-base

WORKDIR /ros2_ws

# Real Nav2 + SLAM Toolbox apt packages for ROS 2 Humble.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-slam-toolbox \
    ros-humble-tf2-ros \
    ros-humble-tf2-tools \
    ros-humble-rosidl-default-generators \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir requests

COPY services/ros2-nav-slam-minilab/axon_nav_slam_interfaces \
     /ros2_ws/src/axon_nav_slam_interfaces
COPY services/ros2-nav-slam-minilab/axon_nav_slam_minilab \
     /ros2_ws/src/axon_nav_slam_minilab

RUN . /opt/ros/humble/setup.sh && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -y -r || true && \
    colcon build --symlink-install

ENV AXON_API_BASE=http://api:8000
ENV ROS_DOMAIN_ID=42
# Synthetic data publish rates (B3) — overridable via compose env.
# Defaults include runtime margin over the QA gates (/scan >=10 Hz, /odom >=20 Hz).
ENV SCAN_HZ=12
ENV ODOM_HZ=25
ENV TF_HZ=25
ENV NAV_SLAM_HEARTBEAT_HZ=1

CMD ["/bin/bash", "-c", "source /opt/ros/humble/setup.sh && source /ros2_ws/install/setup.bash && ros2 launch axon_nav_slam_minilab nav_slam_minilab.launch.py"]
