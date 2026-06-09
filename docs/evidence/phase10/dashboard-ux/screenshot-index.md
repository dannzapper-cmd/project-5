# Phase 10C-2A — Dashboard UX Screenshot Index

Interactive dashboard UX captures from real local execution (core profile).
Separate from the Phase 10A demo screenshots — these do **not** overwrite them.

- Capture script: `scripts/demo/capture_phase10c2a_dashboard_ux.py`
- Output: `docs/evidence/phase10/dashboard-ux/screenshots/<timestamp>/` and `latest/`
- Viewport: 1440×900; section crops (panel screenshots), not full-page.
- Profile: `core` only — ROS2/Nav2/SLAM shown offline by design.

| # | File | What it shows |
|---|------|----------------|
| 00 | `latest/00_demo_cockpit_top.png` | Live Demo Cockpit: watchlist, recommended flow, guided demo button, "prove it's not static HTML" card. |
| 01 | `latest/01_backend_proof_action_log.png` | Backend Proof panel: live health, WebSocket counters, timestamps, IDs, endpoint links. |
| 02 | `latest/02_failure_injection_visible_effect.png` | Safety Panel after a Low Confidence injection (active failure mode + low confidence true). |
| 03 | `latest/03_hitl_decision_flow.png` | HITL / Safety Gate panel with pending-state guidance and Confirm/Reject controls. |
| 04 | `latest/04_digital_twin_command_feedback.png` | Digital Twin after a Pause command — backend receipt and "waiting for broadcast" feedback. |
| 05 | `latest/05_learning_evidence_panels.png` | Learning Evidence (FL) panel with copy run command / report path actions. |
| 06 | `latest/06_robotics_lab_profile_boundary.png` | Robotics Lab offline boundary: activation command, disabled live buttons, enabled local preview. |
| 07 | `latest/07_guided_demo_mode.png` | Guided demo overlay with step text and Next/Previous/End controls. |

## Reproduce

```bash
make models-generate
docker compose --profile core up -d --build
# wait ~30-60s for telemetry warm-up
.venv/bin/python scripts/demo/capture_phase10c2a_dashboard_ux.py
```

## Honest notes

- Captures use the **core** profile only. The Robotics Lab (Nav2 + SLAM) is offline
  and its live buttons are disabled by design; local preview buttons remain available.
- FL/RL/MLOps panels are artifact-backed / on-demand and may show idle defaults.
- Real local execution; no stock or generated imagery.
- The operator copilot is the deterministic offline mock (advisory only).
