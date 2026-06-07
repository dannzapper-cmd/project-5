r"""MiniLab navigation state machine (pure-Python, rclpy-free, unit testable).

Encapsulates goal validation, simple deterministic path planning, and the
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
        steps = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.05))
        for i in range(steps + 1):
            frac = i / steps
            x = x1 + (x2 - x1) * frac
            y = y1 + (y2 - y1) * frac
            hit = self.world.obstacle_at(x, y, margin=0.05)
            if hit is not None:
                return hit
        return None

    def _interpolate_path(
        self, points: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        path: list[tuple[float, float]] = []
        for start, end in zip(points, points[1:]):
            sx, sy = start
            ex, ey = end
            n = max(2, int(math.hypot(ex - sx, ey - sy) / self.waypoint_spacing_m) + 1)
            segment = [
                (
                    round(sx + (ex - sx) * i / (n - 1), 4),
                    round(sy + (ey - sy) * i / (n - 1), 4),
                )
                for i in range(n)
            ]
            if path:
                segment = segment[1:]
            path.extend(segment)
        return path

    def _detour_candidates(
        self, start: tuple[float, float], goal: tuple[float, float]
    ) -> list[tuple[float, float]]:
        clearance = 0.5
        candidates = [start, goal]
        # Stable patrol-corridor anchors keep routes predictable across demos.
        margin = 0.6
        candidates.extend(
            [
                (margin, margin),
                (self.world.width - margin, margin),
                (self.world.width - margin, self.world.height - margin),
                (margin, self.world.height - margin),
                (self.world.width / 2.0, margin),
                (self.world.width / 2.0, self.world.height - margin),
            ]
        )
        grid_step = 0.6
        x = margin
        while x <= self.world.width - margin + 1e-9:
            y = margin
            while y <= self.world.height - margin + 1e-9:
                candidates.append((round(x, 3), round(y, 3)))
                y += grid_step
            x += grid_step
        for obs in self.world.obstacles:
            for x in (obs.x_min - clearance, obs.x_max + clearance):
                for y in (obs.y_min - clearance, obs.y_max + clearance):
                    candidates.append((round(x, 3), round(y, 3)))

        unique: list[tuple[float, float]] = []
        seen: set[tuple[float, float]] = set()
        for x, y in candidates:
            key = (round(x, 3), round(y, 3))
            if key in seen or not self.world.is_free(x, y, margin=0.12):
                continue
            seen.add(key)
            unique.append(key)
        return unique

    def _plan_visibility_path(
        self, start: tuple[float, float], goal: tuple[float, float]
    ) -> list[tuple[float, float]] | None:
        candidates = self._detour_candidates(start, goal)
        if len(candidates) < 2:
            return None
        goal_idx = candidates.index((round(goal[0], 3), round(goal[1], 3)))
        costs = [math.inf] * len(candidates)
        previous: list[int | None] = [None] * len(candidates)
        costs[0] = 0.0
        remaining = set(range(len(candidates)))

        while remaining:
            current = min(remaining, key=lambda idx: costs[idx])
            remaining.remove(current)
            if current == goal_idx or costs[current] == math.inf:
                break
            cx, cy = candidates[current]
            for idx in list(remaining):
                nx, ny = candidates[idx]
                if self._line_blocked(cx, cy, nx, ny) is not None:
                    continue
                cost = costs[current] + math.hypot(nx - cx, ny - cy)
                if cost < costs[idx]:
                    costs[idx] = cost
                    previous[idx] = current

        if costs[goal_idx] == math.inf:
            return None

        route: list[tuple[float, float]] = []
        cursor: int | None = goal_idx
        while cursor is not None:
            route.append(candidates[cursor])
            cursor = previous[cursor]
        route.reverse()
        return route

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

        sx, sy = start
        self.status = "planning"
        self.reason = "Planning deterministic path to goal."
        block = self._line_blocked(sx, sy, goal_x, goal_y)
        if block is None:
            route = [(sx, sy), (goal_x, goal_y)]
        else:
            route = self._plan_visibility_path((sx, sy), (goal_x, goal_y))
        if route is None:
            self.status = "blocked"
            self.reason = f"No collision-free route around '{block}'."
            return self.status

        self.path = self._interpolate_path(route)
        self.status = "navigating"
        self.reason = "Navigating to goal." if block is None else "Navigating detour to goal."
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
