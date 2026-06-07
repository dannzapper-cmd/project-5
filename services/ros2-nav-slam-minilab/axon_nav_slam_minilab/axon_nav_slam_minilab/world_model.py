"""Deterministic 2D rehab-lab world model for the MiniLab.

Pure-Python (no rclpy / no ROS2 imports) so it can be unit tested in normal CI.
``mini_world_node`` wraps this to publish synthetic ``/scan``, ``/odom`` and TF.

The world is a small rectangular rehab lab bounded by four walls, with a set of
interior obstacles/landmarks. A LaserScan is computed by ray-casting against all
wall and obstacle segments — this gives SLAM Toolbox real geometric features to
map (not a constant fake array).

Coordinates are in meters in the ``map`` frame. Origin (0, 0) is the
bottom-left corner of the lab. Angles are radians.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

Segment = tuple[float, float, float, float]  # (x1, y1, x2, y2)


@dataclass(frozen=True)
class Rect:
    """Axis-aligned rectangle obstacle/landmark."""

    name: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        return (
            self.x_min - margin <= x <= self.x_max + margin
            and self.y_min - margin <= y <= self.y_max + margin
        )

    def segments(self) -> list[Segment]:
        return [
            (self.x_min, self.y_min, self.x_max, self.y_min),
            (self.x_max, self.y_min, self.x_max, self.y_max),
            (self.x_max, self.y_max, self.x_min, self.y_max),
            (self.x_min, self.y_max, self.x_min, self.y_min),
        ]


@dataclass
class WorldModel:
    """A small deterministic 2D rehab lab with walls and obstacles."""

    width: float = 6.0
    height: float = 4.0
    obstacles: list[Rect] = field(default_factory=list)
    range_min: float = 0.12
    range_max: float = 8.0

    def __post_init__(self) -> None:
        if not self.obstacles:
            # Four interior obstacles/landmarks (rehab equipment) + a divider wall.
            self.obstacles = [
                Rect("treadmill", 1.0, 0.4, 1.8, 1.4),
                Rect("parallel_bars", 3.8, 0.5, 4.6, 2.2),
                Rect("mat_stack", 0.5, 2.8, 1.6, 3.4),
                Rect("pillar", 2.8, 2.9, 3.2, 3.3),
                Rect("storage_cart", 4.9, 2.9, 5.5, 3.5),
            ]

    def wall_segments(self) -> list[Segment]:
        return [
            (0.0, 0.0, self.width, 0.0),
            (self.width, 0.0, self.width, self.height),
            (self.width, self.height, 0.0, self.height),
            (0.0, self.height, 0.0, 0.0),
        ]

    def all_segments(self) -> list[Segment]:
        segs = self.wall_segments()
        for obs in self.obstacles:
            segs.extend(obs.segments())
        return segs

    def is_free(self, x: float, y: float, margin: float = 0.18) -> bool:
        """True if (x, y) is inside the lab and clear of obstacles (+margin)."""
        if not (margin <= x <= self.width - margin and margin <= y <= self.height - margin):
            return False
        return all(not obs.contains(x, y, margin) for obs in self.obstacles)

    def obstacle_at(self, x: float, y: float, margin: float = 0.0) -> str | None:
        for obs in self.obstacles:
            if obs.contains(x, y, margin):
                return obs.name
        return None

    @staticmethod
    def _ray_segment_distance(
        ox: float, oy: float, dx: float, dy: float, seg: Segment
    ) -> float | None:
        """Distance along ray (origin o, unit dir d) to segment, or None."""
        x1, y1, x2, y2 = seg
        sx = x2 - x1
        sy = y2 - y1
        denom = dx * sy - dy * sx
        if abs(denom) < 1e-12:
            return None
        # Solve o + t*d = p1 + u*s
        t = ((x1 - ox) * sy - (y1 - oy) * sx) / denom
        u = ((x1 - ox) * dy - (y1 - oy) * dx) / denom
        if t >= 0.0 and 0.0 <= u <= 1.0:
            return t
        return None

    def raycast(self, x: float, y: float, angle: float) -> float:
        """Return distance from (x, y) along global ``angle`` to nearest segment."""
        dx = math.cos(angle)
        dy = math.sin(angle)
        best = self.range_max
        for seg in self.all_segments():
            dist = self._ray_segment_distance(x, y, dx, dy, seg)
            if dist is not None and dist < best:
                best = dist
        return max(self.range_min, min(best, self.range_max))

    def compute_scan(
        self,
        x: float,
        y: float,
        heading: float,
        num_readings: int = 180,
        angle_min: float = -math.pi,
        angle_max: float = math.pi,
    ) -> list[float]:
        """Compute LaserScan ranges (robot frame) at the given pose."""
        if num_readings < 2:
            num_readings = 2
        increment = (angle_max - angle_min) / (num_readings - 1)
        ranges: list[float] = []
        for i in range(num_readings):
            beam = heading + angle_min + i * increment
            ranges.append(round(self.raycast(x, y, beam), 4))
        return ranges


@dataclass
class PatrolTrajectory:
    """Deterministic patrol path so the robot roams and SLAM can build a map.

    Robot follows a closed rounded-rectangle loop inside the lab at constant
    speed. With a fixed seed-free analytic path the motion is fully reproducible.
    """

    world: WorldModel
    speed_mps: float = 0.35
    margin: float = 0.6

    def __post_init__(self) -> None:
        w, h, m = self.world.width, self.world.height, self.margin
        self._waypoints: list[tuple[float, float]] = [
            (m, m),
            (w - m, m),
            (w - m, h - m),
            (m, h - m),
        ]
        self._seg_index = 0
        self._t = 0.0

    def waypoints(self) -> list[tuple[float, float]]:
        return list(self._waypoints)

    def pose_at(self, elapsed: float) -> tuple[float, float, float]:
        """Return (x, y, heading) at ``elapsed`` seconds along the patrol loop."""
        # Segment lengths around the loop.
        pts = self._waypoints
        seg_lengths = []
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            seg_lengths.append(math.hypot(x2 - x1, y2 - y1))
        perimeter = sum(seg_lengths)
        travelled = (elapsed * self.speed_mps) % perimeter
        for i, length in enumerate(seg_lengths):
            if travelled <= length:
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % len(pts)]
                frac = travelled / length if length else 0.0
                x = x1 + (x2 - x1) * frac
                y = y1 + (y2 - y1) * frac
                heading = math.atan2(y2 - y1, x2 - x1)
                return (x, y, heading)
            travelled -= length
        x0, y0 = pts[0]
        return (x0, y0, 0.0)
