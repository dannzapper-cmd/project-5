# ADR-005: ROS2 Thin Adapter and Mandatory Nav2 + SLAM MiniLab

- **Status:** Proposed
- **Date:** 2026-06-05

## Context

AXON integrates with robotics software through a thin adapter without requiring physical hardware. An advanced **mandatory** phase (5.5) must demonstrate Nav2 navigation and SLAM in a MiniLab profile separate from daily development.

Gazebo, Isaac, and Omniverse are not core dependencies.

## Decision to Evaluate

1. **ROS2 thin adapter** translating AXON events to/from ROS2 topics, services, and actions
2. **Separate `ros2-nav-slam` profile** for Nav2 + SLAM MiniLab (Phase 5.5 — mandatory advanced)

## Options to Compare

| Option | Pros | Cons |
|--------|------|------|
| Thin adapter + isolated MiniLab | Clear boundaries, profile isolation | Two ROS integration modes to maintain |
| Full ROS2 core always-on | Single integration path | Too heavy for default dev |
| Skip ROS2 entirely | Simpler | Violates mandatory roadmap |

## Evidence Needed

- ROS2 topic/service/action screenshots (Phase 5)
- Nav2 + SLAM MiniLab video (Phase 5.5)
- Rehab route execution with safety pause (Phase 5.5)

## Future Phase

- Phase 5 — Digital Twin + ROS2 Core
- Phase 5.5 — Full ROS2 Nav2 + SLAM MiniLab (mandatory)
