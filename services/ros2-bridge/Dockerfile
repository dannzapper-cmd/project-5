FROM ros:humble-ros-base

WORKDIR /ros2_ws/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    ros-humble-rosidl-default-generators \
    && rm -rf /var/lib/apt/lists/*

COPY services/ros2-bridge /ros2_ws/src/axon_ros2_bridge
RUN pip3 install --no-cache-dir requests

WORKDIR /ros2_ws
RUN . /opt/ros/humble/setup.sh && \
    rosdep update && rosdep install --from-paths src --ignore-src -y -r && \
    colcon build --symlink-install

ENV AXON_API_BASE=http://api:8000
ENV ROS2_TWIN_POLL_HZ=2
ENV ROS_DOMAIN_ID=42

CMD ["/bin/bash", "-c", "source /opt/ros/humble/setup.sh && source /ros2_ws/install/setup.bash && ros2 launch axon_ros2_bridge axon_bridge.launch.py"]
