r"""MiniLab navigation state machine (pure-Python, rclpy-free, unit testable).

Encapsulates goal validation, simple straight-line path planning, and the
status transitions used by ``nav_goal_runner``:

    idle -> planning -> navigating -> reached
                     \-> blocked   (goal invalid / inside obstacle)
                     \-> failed    (lost progress / aborted)

This is intentionally a lightweight, deterministic planner so the MiniLab
demos produce honest, reproducible status flows even before a full Nav2
lifecycle runtime is validated by local QA. The same map/pose data is fed to
real SLAM Toolbox and (where feasible) the Nav2 stack; see the launch file.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from axon_nav_slam_minilab.world_model import WorldModel

Status = str  # one of: idle, planning, navigating, reached, blocked, failed


@dataclass
class NavStateMachine:
    world: WorldModel
    goal_tolerance_m: float = 0.25
    waypoint_spacing_m: float = 0.3
    progress_timeout_s: float = 25.0

    status: Status = "idle"
    reason: str | None = None
    goal: tuple[float, float, float] | None = None
    path: list[tuple[float, float]] = field(default_factory=list)
    _last_distance: float = math.inf
    _stalled_for: float = 0.0
    active_demo: str | None = None

    def reset(self) -> None:
        self.status = "idle"
        self.reason = None
        self.goal = None
        self.path = []
        self._last_distance = math.inf
        self._stalled_for = 0.0
        self.active_demo = None

    def _line_blocked(self, x1: float, y1: float, x2: float, y2: float) -> str | None:
        """Return blocking obstacle name if the straight segment is obstructed."""
        steps = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.1))
        for i in range(steps + 1):
            frac = i / steps
            x = x1 + (x2 - x1) * frac
            y = y1 + (y2 - y1) * frac
            hit = self.world.obstacle_at(x, y, margin=0.05)
            if hit is not None:
                return hit
        return None

    def plan(
        self,
        start: tuple[float, float],
        goal_x: float,
        goal_y: float,
        goal_theta_deg: float = 0.0,
        demo: str | None = None,
    ) -> Status:
        """Validate and plan a path to the goal. Returns the resulting status."""
        self.active_demo = demo
        self.goal = (goal_x, goal_y, goal_theta_deg)
        self.path = []
        self._last_distance = math.inf
        self._stalled_for = 0.0

        inside = self.world.obstacle_at(goal_x, goal_y, margin=0.0)
        if inside is not None:
            self.status = "blocked"
            self.reason = f"Goal lies inside obstacle '{inside}'."
            return self.status
        if not self.world.is_free(goal_x, goal_y, margin=0.12):
            self.status = "blocked"
            self.reason = "Goal is out of bounds or too close to a wall."
            return self.status

        self.status = "planning"
        self.reason = "Planning straight-line path to goal."
        sx, sy = start
        block = self._line_blocked(sx, sy, goal_x, goal_y)
        if block is not None:
            # Honest behaviour: direct path obstructed; the lightweight planner
            # cannot route around it, so report blocked with the obstacle name.
            self.status = "blocked"
            self.reason = f"Direct path obstructed by '{block}' (no detour planner)."
            return self.status

        n = max(2, int(math.hypot(goal_x - sx, goal_y - sy) / self.waypoint_spacing_m) + 1)
        self.path = [
            (
                round(sx + (goal_x - sx) * i / (n - 1), 4),
                round(sy + (goal_y - sy) * i / (n - 1), 4),
            )
            for i in range(n)
        ]
        self.status = "navigating"
        self.reason = "Navigating to goal."
        return self.status

    def update(self, robot_x: float, robot_y: float, dt: float = 0.0) -> Status:
        """Advance status given the current robot pose."""
        if self.status not in ("navigating", "planning") or self.goal is None:
            return self.status
        gx, gy, _ = self.goal
        dist = math.hypot(gx - robot_x, gy - robot_y)
        if dist <= self.goal_tolerance_m:
            self.status = "reached"
            self.reason = "Goal reached."
            return self.status
        if self.status == "planning":
            self.status = "navigating"
        # Stall detection -> failed (honest, no fake success).
        if dist >= self._last_distance - 1e-3:
            self._stalled_for += dt
        else:
            self._stalled_for = 0.0
        self._last_distance = dist
        if self._stalled_for >= self.progress_timeout_s:
            self.status = "failed"
            self.reason = "No progress toward goal (timeout)."
        return self.status

    def path_length_m(self) -> float:
        total = 0.0
        for i in range(1, len(self.path)):
            x1, y1 = self.path[i - 1]
            x2, y2 = self.path[i]
            total += math.hypot(x2 - x1, y2 - y1)
        return round(total, 4)
