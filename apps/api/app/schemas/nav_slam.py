"""Phase 5.5 ROS2 Nav2 + SLAM MiniLab state and command contracts.

These versioned schemas live in the same schemas module used by
``DigitalTwinStateV1`` (``apps/api/app/schemas/twin.py``). They are imported by:

- backend API routes (``apps.api.app.routes.nav_slam``)
- backend service (``apps.api.app.nav_slam.service``)
- tests (``tests/test_phase5_5_nav_slam.py``)
- the ROS2 bridge (``services/ros2-nav-slam-minilab/.../axon_nav_slam_bridge.py``)

The MiniLab is a *simulated* robotics navigation/mapping lab. No physical
robot, no clinical autonomy, no medical claims, no patient data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

NavStatus = Literal[
    "idle",
    "planning",
    "navigating",
    "reached",
    "blocked",
    "failed",
]
SlamStatus = Literal["inactive", "mapping", "stable", "degraded"]
NavSlamBridgeStatus = Literal["online", "offline", "degraded"]
NavSlamCommandName = Literal["start_mapping", "send_goal", "reset"]
NavSlamCommandStatus = Literal["accepted", "rejected", "blocked"]


class NavGoalV1(BaseModel):
    """A simple 2D navigation goal in the MiniLab map frame (meters / degrees)."""

    schema_version: Literal["v1"] = "v1"
    x: float = 0.0
    y: float = 0.0
    theta_deg: float = 0.0
    frame_id: str = "map"
    label: str | None = None


class NavPathV1(BaseModel):
    """Planned path summary as a list of 2D waypoints in the map frame."""

    schema_version: Literal["v1"] = "v1"
    frame_id: str = "map"
    waypoints: list[tuple[float, float]] = Field(default_factory=list)
    length_m: float = 0.0
    waypoint_count: int = 0


class SlamMapStatusV1(BaseModel):
    """SLAM map coverage / update metrics derived from the occupancy grid."""

    schema_version: Literal["v1"] = "v1"
    status: SlamStatus = "inactive"
    resolution_m: float | None = None
    width_cells: int | None = None
    height_cells: int | None = None
    known_cells: int = 0
    total_cells: int = 0
    coverage_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    map_updates: int = 0
    last_update: datetime | None = None


class NavSlamStateV1(BaseModel):
    """Versioned snapshot of MiniLab navigation + SLAM state for AXON."""

    schema_version: Literal["v1"] = "v1"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    bridge_status: NavSlamBridgeStatus = "offline"
    nav_status: NavStatus = "idle"
    nav_status_reason: str | None = None
    active_demo: str | None = None
    robot_pose: tuple[float, float, float] = (0.0, 0.0, 0.0)
    goal: NavGoalV1 | None = None
    path: NavPathV1 = Field(default_factory=NavPathV1)
    slam: SlamMapStatusV1 = Field(default_factory=SlamMapStatusV1)
    last_heartbeat: datetime | None = None
    trace_id: str | None = None


class NavSlamCommandRequestV1(BaseModel):
    """Command request for the MiniLab navigation/mapping flow."""

    schema_version: Literal["v1"] = "v1"
    command: NavSlamCommandName
    requested_by: str
    goal: NavGoalV1 | None = None
    demo: str | None = None
    reason: str | None = None


class NavSlamCommandResponseV1(BaseModel):
    """Outcome of a MiniLab command with trace linkage."""

    schema_version: Literal["v1"] = "v1"
    status: NavSlamCommandStatus
    command: str
    reason: str | None = None
    trace_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NavSlamIngestV1(BaseModel):
    """Payload pushed from the ROS2 bridge into the AXON backend.

    Carries the live MiniLab state observed on ROS2 topics so the backend can
    mirror it for the dashboard. All fields optional so partial updates work.
    """

    schema_version: Literal["v1"] = "v1"
    nav_status: NavStatus | None = None
    nav_status_reason: str | None = None
    active_demo: str | None = None
    robot_pose: tuple[float, float, float] | None = None
    goal: NavGoalV1 | None = None
    path: NavPathV1 | None = None
    slam: SlamMapStatusV1 | None = None
    trace_id: str | None = None
