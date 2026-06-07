"""ROS2 bridge package structure smoke tests (no ROS2 runtime in CI)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "services" / "ros2-bridge"


def test_ros2_package_xml_exists() -> None:
    assert (BRIDGE / "package.xml").is_file()
    content = (BRIDGE / "package.xml").read_text(encoding="utf-8")
    assert "axon_ros2_bridge" in content
    assert "rclpy" in content


def test_ros2_cmake_and_srv() -> None:
    assert (BRIDGE / "CMakeLists.txt").is_file()
    assert (BRIDGE / "srv" / "TwinCommand.srv").is_file()
    srv = (BRIDGE / "srv" / "TwinCommand.srv").read_text(encoding="utf-8")
    assert "command" in srv
    assert "trace_id" in srv


def test_ros2_launch_and_node() -> None:
    assert (BRIDGE / "launch" / "axon_bridge.launch.py").is_file()
    node = (BRIDGE / "axon_ros2_bridge" / "twin_bridge_node.py").read_text(encoding="utf-8")
    assert "/axon/twin/state" in node
    assert "/axon/command" in node
    assert "rclpy" in node


def test_ros2_dockerfile_uses_official_image() -> None:
    dockerfile = (BRIDGE / "Dockerfile").read_text(encoding="utf-8")
    assert "ros:humble" in dockerfile


def test_compose_ros2_profile() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "ros2_bridge:" in compose
    assert "profiles: [ros2, full]" in compose
