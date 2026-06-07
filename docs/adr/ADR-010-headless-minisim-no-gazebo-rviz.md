# ADR-010: Headless Mini-Sim Instead of Gazebo / RViz / Physical Robot (Fase 5.5)

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** AXON project owners
- **Related:** ADR-009 (Nav2 + SLAM MiniLab scope)

## Context

A Nav2 + SLAM demonstration normally relies on Gazebo/Ignition (physics sim)
plus RViz (GUI) and/or a physical robot. Those are heavy, GUI-bound, and a poor
fit for a reproducible, headless, profile-isolated portfolio lab that must run
on modest machines and in CI-adjacent environments.

## Decision

Use a **custom headless mini-sim** (`mini_world_node`) that publishes synthetic
but geometrically meaningful sensor + TF data, instead of Gazebo/RViz/hardware.

- **World:** a deterministic 2D rehab lab (6 m × 4 m) with four walls and five
  interior obstacles/landmarks (treadmill, parallel bars, mat stack, pillar,
  storage cart). Documented in `config/world.yaml` and built identically in
  `world_model.py`.
- **Scan:** `/scan` (`sensor_msgs/LaserScan`) computed by ray-casting against
  all wall/obstacle segments — real geometric features for SLAM, not a constant
  fake array. Default 180 beams, ≥ 10 Hz.
- **Odometry + TF:** `/odom` and `odom->base_link` at ≥ 20 Hz from a deterministic
  patrol trajectory; SLAM Toolbox supplies `map->odom`.
- **No GUI:** evidence is collected with `ros2 node list`, `ros2 topic hz`,
  `ros2 topic echo`, `ros2 run tf2_tools view_frames`, and the lightweight
  dashboard SVG panel — never RViz.

## Alternatives considered

| Option | Why rejected |
|--------|--------------|
| Gazebo/Ignition | Heavy, GPU/physics, slow, GUI-oriented; banned by scope |
| RViz as required | GUI dependency; banned by scope |
| Physical robot | No hardware; out of scope; safety/claims risk |
| Pre-baked static map replay | Would not demonstrate *real* online SLAM |

## Consequences

- The MiniLab is reproducible, deterministic, small, and headless.
- SLAM Toolbox and Nav2 receive valid inputs and run as real ROS2 nodes.
- The synthetic world is documented and unit-tested (no fake success states).
- Rendering in the dashboard uses lightweight SVG only — no 3D dependencies.

## Constraints restated

Simulated robotics lab only. No physical robot. No patient data. No medical
claims. No clinical autonomy. Core profile remains independent. This ADR does
not introduce Fase 6.
