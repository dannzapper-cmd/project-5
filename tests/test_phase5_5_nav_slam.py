"""Phase 5.5 ROS2 Nav2 + SLAM MiniLab tests.

Covers versioned schemas, backend API (status/goal/command/ingest/pending),
Docker Compose profile isolation, ROS2 package structure, and the pure-Python
MiniLab logic (world model + nav state machine). Full ROS2/Nav2/SLAM runtime is
verified by local QA — not in CI (no Docker/ROS2 runtime here).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml
from apps.api.app.nav_slam import service as nav_slam_service
from apps.api.app.schemas.nav_slam import (
    NavGoalV1,
    NavPathV1,
    NavSlamCommandRequestV1,
    NavSlamCommandResponseV1,
    NavSlamIngestV1,
    NavSlamStateV1,
    SlamMapStatusV1,
)
from apps.api.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
MINILAB = ROOT / "services" / "ros2-nav-slam-minilab"
PKG = MINILAB / "axon_nav_slam_minilab"
INTERFACES = MINILAB / "axon_nav_slam_interfaces"

# Make the rclpy-free MiniLab logic importable for unit tests.
sys.path.insert(0, str(PKG))
from axon_nav_slam_minilab.nav_state_machine import NavStateMachine  # noqa: E402
from axon_nav_slam_minilab.world_model import PatrolTrajectory, WorldModel  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_nav_slam_state():
    nav_slam_service.reset_state()
    yield
    nav_slam_service.reset_state()


@pytest.fixture
def client():
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
def test_nav_slam_state_v1_serializes():
    state = NavSlamStateV1(nav_status="navigating", bridge_status="online")
    data = state.model_dump(mode="json")
    assert data["schema_version"] == "v1"
    assert data["nav_status"] == "navigating"
    assert data["slam"]["schema_version"] == "v1"
    assert data["path"]["schema_version"] == "v1"


def test_nav_goal_v1_validation():
    goal = NavGoalV1(x=5.0, y=1.0, theta_deg=90.0, label="demo")
    assert goal.schema_version == "v1"
    assert goal.frame_id == "map"
    with pytest.raises(ValidationError):
        NavGoalV1(x="not-a-number")  # type: ignore[arg-type]


def test_nav_path_and_slam_map_status_serialize():
    path = NavPathV1(waypoints=[(0.0, 0.0), (1.0, 1.0)], length_m=1.41, waypoint_count=2)
    assert path.model_dump(mode="json")["waypoint_count"] == 2
    slam = SlamMapStatusV1(status="mapping", coverage_pct=42.5, known_cells=10, total_cells=100)
    assert slam.model_dump(mode="json")["coverage_pct"] == 42.5
    with pytest.raises(ValidationError):
        SlamMapStatusV1(coverage_pct=150.0)


def test_nav_slam_command_request_response_serialize():
    req = NavSlamCommandRequestV1(
        command="send_goal", requested_by="qa", goal=NavGoalV1(x=1.0, y=2.0)
    )
    assert req.model_dump(mode="json")["command"] == "send_goal"
    resp = NavSlamCommandResponseV1(status="accepted", command="send_goal", trace_id="t-1")
    assert resp.model_dump(mode="json")["schema_version"] == "v1"
    with pytest.raises(ValidationError):
        NavSlamCommandRequestV1(command="not_a_command", requested_by="qa")  # type: ignore[arg-type]


def test_nav_slam_ingest_partial_update():
    ingest = NavSlamIngestV1(nav_status="planning", robot_pose=(1.0, 2.0, 0.5))
    assert ingest.robot_pose == (1.0, 2.0, 0.5)


# --------------------------------------------------------------------------- #
# Backend command validation + service
# --------------------------------------------------------------------------- #
def test_send_goal_requires_goal():
    resp = nav_slam_service.handle_command(
        NavSlamCommandRequestV1(command="send_goal", requested_by="qa")
    )
    assert resp.status == "rejected"
    assert resp.trace_id


def test_send_goal_accepted_enqueues_command():
    resp = nav_slam_service.handle_command(
        NavSlamCommandRequestV1(
            command="send_goal", requested_by="qa", goal=NavGoalV1(x=5.0, y=1.0)
        )
    )
    assert resp.status == "accepted"
    pending = nav_slam_service.get_pending_command(after_seq=0)
    assert pending is not None
    assert pending["command"] == "send_goal"
    assert nav_slam_service.get_pending_command(after_seq=pending["seq"]) is None


def test_reset_and_start_mapping_commands_accepted():
    assert (
        nav_slam_service.handle_command(
            NavSlamCommandRequestV1(command="reset", requested_by="qa")
        ).status
        == "accepted"
    )
    assert (
        nav_slam_service.handle_command(
            NavSlamCommandRequestV1(command="start_mapping", requested_by="qa")
        ).status
        == "accepted"
    )


def test_bridge_offline_until_ingest():
    state = nav_slam_service.get_nav_slam_state()
    assert state.bridge_status == "offline"
    nav_slam_service.update_from_ingest(NavSlamIngestV1(nav_status="navigating"))
    assert nav_slam_service.get_nav_slam_state().bridge_status == "online"


# --------------------------------------------------------------------------- #
# Backend API endpoints
# --------------------------------------------------------------------------- #
def test_api_status_offline_graceful(client):
    res = client.get("/api/v1/nav-slam/status")
    assert res.status_code == 200
    body = res.json()
    assert body["bridge_status"] == "offline"
    assert "safety_notice" in body


def test_api_goal_endpoint(client):
    res = client.post("/api/v1/nav-slam/goal", json={"x": 5.0, "y": 1.0, "theta_deg": 0.0})
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"


def test_api_command_requires_requested_by(client):
    res = client.post(
        "/api/v1/nav-slam/command",
        json={"command": "reset", "requested_by": "  "},
    )
    assert res.status_code == 422


def test_api_ingest_then_status_online(client):
    res = client.post(
        "/api/v1/nav-slam/ingest",
        json={"nav_status": "mapping" if False else "planning", "robot_pose": [1.0, 1.0, 0.0]},
    )
    assert res.status_code == 200
    status = client.get("/api/v1/nav-slam/status").json()
    assert status["bridge_status"] == "online"
    assert status["nav_status"] == "planning"


def test_api_pending_command_flow(client):
    client.post(
        "/api/v1/nav-slam/command",
        json={"command": "send_goal", "requested_by": "qa", "goal": {"x": 5.0, "y": 1.0}},
    )
    pending = client.get("/api/v1/nav-slam/pending-command", params={"after_seq": 0}).json()
    assert pending["command"] == "send_goal"
    seq = pending["seq"]
    again = client.get("/api/v1/nav-slam/pending-command", params={"after_seq": seq}).json()
    assert again["command"] is None


def test_health_includes_nav_slam(client):
    body = client.get("/health").json()
    assert "nav_slam_minilab" in body
    assert body["nav_slam_minilab"]["bridge_status"] in ("offline", "online", "degraded")


# --------------------------------------------------------------------------- #
# Docker Compose profile isolation
# --------------------------------------------------------------------------- #
def _load_compose() -> dict:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_compose_nav_slam_profile_exists():
    compose = _load_compose()
    svc = compose["services"]["ros2_nav_slam"]
    assert "ros2-nav-slam" in svc["profiles"]
    assert "full" in svc["profiles"]
    assert svc["build"]["dockerfile"].endswith("ros2-nav-slam-minilab/Dockerfile")


def test_core_does_not_depend_on_nav_slam():
    compose = _load_compose()
    core_services = [
        name
        for name, svc in compose["services"].items()
        if "core" in (svc.get("profiles") or [])
    ]
    assert "ros2_nav_slam" not in core_services
    for name in core_services:
        svc = compose["services"][name]
        deps = svc.get("depends_on") or {}
        dep_names = deps if isinstance(deps, list) else list(deps.keys())
        assert "ros2_nav_slam" not in dep_names
    # MiniLab must not pull the whole core in via depends_on either.
    assert "depends_on" not in compose["services"]["ros2_nav_slam"]


def test_compose_nav_slam_publish_rate_env():
    svc = _load_compose()["services"]["ros2_nav_slam"]
    env = svc["environment"]
    for key in ("SCAN_HZ", "ODOM_HZ", "TF_HZ", "NAV_SLAM_HEARTBEAT_HZ"):
        assert key in env
    assert int(env["SCAN_HZ"].split(":-", 1)[1].rstrip("}")) >= 12
    assert int(env["ODOM_HZ"].split(":-", 1)[1].rstrip("}")) >= 25
    assert int(env["TF_HZ"].split(":-", 1)[1].rstrip("}")) >= 25


def test_env_example_declares_publish_rates():
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ("SCAN_HZ", "ODOM_HZ", "TF_HZ", "NAV_SLAM_HEARTBEAT_HZ"):
        assert key in env


# --------------------------------------------------------------------------- #
# ROS2 package structure
# --------------------------------------------------------------------------- #
def test_minilab_package_structure():
    assert (PKG / "package.xml").is_file()
    assert (PKG / "setup.py").is_file()
    assert (PKG / "resource" / "axon_nav_slam_minilab").is_file()
    assert (PKG / "launch" / "nav_slam_minilab.launch.py").is_file()
    assert (PKG / "config" / "slam_toolbox_params.yaml").is_file()
    assert (PKG / "config" / "nav2_params.yaml").is_file()
    assert (PKG / "config" / "world.yaml").is_file()
    for node in (
        "mini_world_node.py",
        "nav_goal_runner.py",
        "slam_status_node.py",
        "axon_nav_slam_bridge.py",
    ):
        assert (PKG / "axon_nav_slam_minilab" / node).is_file()


def test_interfaces_package_structure():
    assert (INTERFACES / "package.xml").is_file()
    assert (INTERFACES / "CMakeLists.txt").is_file()
    srv = (INTERFACES / "srv" / "SendNavGoal.srv").read_text(encoding="utf-8")
    assert "theta_deg" in srv
    assert "trace_id" in srv


def test_minilab_uses_humble_and_nav2_slam_packages():
    dockerfile = (MINILAB / "Dockerfile").read_text(encoding="utf-8")
    assert "ros:humble" in dockerfile
    for pkg in (
        "ros-humble-navigation2",
        "ros-humble-nav2-bringup",
        "ros-humble-slam-toolbox",
    ):
        assert pkg in dockerfile


def test_bridge_has_integration_inventory():
    bridge = (PKG / "axon_nav_slam_minilab" / "axon_nav_slam_bridge.py").read_text(
        encoding="utf-8"
    )
    assert "Integration Inventory" in bridge
    assert "ros:humble" in bridge
    assert "schemas/nav_slam.py" in bridge


def test_slam_params_online_async_frames():
    params = yaml.safe_load(
        (PKG / "config" / "slam_toolbox_params.yaml").read_text(encoding="utf-8")
    )["slam_toolbox"]["ros__parameters"]
    assert params["odom_frame"] == "odom"
    assert params["map_frame"] == "map"
    assert params["base_frame"] == "base_link"
    assert params["scan_topic"] == "/scan"
    assert params["use_scan_matching"] is True
    assert params["use_sim_time"] is False
    assert params["mode"] == "mapping"
    assert params["solver_plugin"] == "solver_plugins::CeresSolver"


def test_launch_uses_online_async_and_nav2_bringup():
    launch = (PKG / "launch" / "nav_slam_minilab.launch.py").read_text(encoding="utf-8")
    assert "online_async_launch.py" in launch
    assert "navigation_launch.py" in launch
    assert "TimerAction" in launch


# --------------------------------------------------------------------------- #
# Pure-Python MiniLab logic (rclpy-free)
# --------------------------------------------------------------------------- #
def test_world_has_features_for_slam():
    world = WorldModel()
    assert len(world.obstacles) >= 4
    # Scan must produce varied, finite ranges (not a constant fake array).
    ranges = world.compute_scan(3.0, 2.0, 0.0, num_readings=180)
    assert len(ranges) == 180
    assert all(world.range_min <= r <= world.range_max for r in ranges)
    assert len(set(round(r, 2) for r in ranges)) > 5


def test_world_free_space_and_obstacle_detection():
    world = WorldModel()
    assert world.obstacle_at(1.4, 0.9) == "treadmill"
    assert world.obstacle_at(3.0, 2.0) is None
    assert world.is_free(3.0, 2.0)
    assert not world.is_free(1.4, 0.9)


def test_patrol_trajectory_deterministic_and_in_bounds():
    world = WorldModel()
    patrol = PatrolTrajectory(world)
    p1 = patrol.pose_at(5.0)
    p2 = PatrolTrajectory(world).pose_at(5.0)
    assert p1 == p2
    x, y, _ = p1
    assert 0.0 < x < world.width and 0.0 < y < world.height


def test_nav_state_machine_reachable_goal():
    world = WorldModel()
    sm = NavStateMachine(world)
    # Clear vertical corridor at x=5.0 (free of all obstacles).
    status = sm.plan((5.0, 2.5), 5.0, 1.0)
    assert status == "navigating"
    assert sm.path
    assert sm.path_length_m() > 0
    # Robot arrives -> reached (no fake success before arrival).
    assert sm.update(5.0, 1.8) in ("navigating", "reached")
    assert sm.update(5.0, 1.0) == "reached"


def test_nav_state_machine_reachable_demo_detours_around_obstacle():
    world = WorldModel()
    sm = NavStateMachine(world)
    status = sm.plan((0.678, 0.6), 5.0, 1.0, demo="nav_goal_demo")
    assert status == "navigating"
    assert sm.reason == "Navigating detour to goal."
    assert sm.path[0] == (0.678, 0.6)
    assert sm.path[-1] == (5.0, 1.0)
    assert len(sm.path) > 2
    assert all(
        sm._line_blocked(x1, y1, x2, y2) is None
        for (x1, y1), (x2, y2) in zip(sm.path, sm.path[1:], strict=False)
    )


def test_nav_state_machine_blocked_goal_inside_obstacle():
    world = WorldModel()
    sm = NavStateMachine(world)
    status = sm.plan((0.5, 1.0), 4.2, 1.3, demo="blocked_goal_demo")
    assert status == "blocked"
    assert sm.reason and "parallel_bars" in sm.reason


def test_nav_state_machine_reset():
    world = WorldModel()
    sm = NavStateMachine(world)
    sm.plan((3.0, 2.0), 5.0, 1.0)
    sm.reset()
    assert sm.status == "idle"
    assert sm.goal is None


# --------------------------------------------------------------------------- #
# Scope / claims audit (no Fase 6, no medical claims in new code/docs)
# --------------------------------------------------------------------------- #
def test_scope_audit_minilab_docs_are_honest():
    readme = (MINILAB / "README.md").read_text(encoding="utf-8").lower()
    assert "no physical robot" in readme
    assert "no medical claims" in readme or "no clinical autonomy" in readme


def test_no_forbidden_scope_terms_in_minilab_package():
    forbidden = ["federated learning", "reinforcement learning", "kubernetes", "gazebo"]
    for py in PKG.rglob("*.py"):
        text = py.read_text(encoding="utf-8").lower()
        for term in forbidden:
            # Allow "no gazebo" style negations in docstrings.
            assert f"no {term}" in text or term not in text, f"{term} in {py}"
