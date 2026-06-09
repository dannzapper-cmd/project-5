# Phase 10C-2A — Interactive Dashboard Activation & Backend Proof Layer

Closeout record for the dashboard UX hardening pass that turns the AXON dashboard
into an interactive, evidence-backed operations cockpit before the final demo
recording. No video, no release, no cloud, no fake capabilities.

> Synthetic data only. Not a medical device. No clinical use. Operator copilot is
> advisory only. ROS2/Nav2/SLAM is offline in core by design.

---

## Summary

- **Branch:** `feat/phase-10c2a-interactive-dashboard-proof`
- **Base:** `main` after Phase 10C-1, Enterprise Production Path (#21), and Fresh
  Clone Demo Checklist (#22) — base commit `d9b92b2`.
- **Scope:** dashboard (`apps/dashboard/*`), one small read-only backend route
  (`apps/api/app/routes/system.py`), docs, and a separate screenshot script.
- **Goal:** answer "How can a reviewer tell this is a real running system and not
  static HTML?" with live backend proof, action receipts, an event timeline,
  per-button feedback, a guided demo, clear capability boundaries, and exact
  activation commands.

---

## Files changed

| File | Change |
|------|--------|
| `apps/dashboard/index.html` | New cockpit, backend-proof, capabilities, action-log, copilot panels; capability labels replace phase badges; improved HITL / failure-injection / learning / robotics-lab markup; guided-demo overlay + toast container. |
| `apps/dashboard/app.js` | Action log, toasts, pulse/scroll helpers, backend-proof polling, capabilities matrix, copilot panel, guided demo, robotics-lab offline detection + local preview, per-button receipts. |
| `apps/dashboard/styles.css` | Styling for all new components (cockpit, proof grid, action log, toasts, pulse animation, guided demo overlay, failure badge, capabilities). |
| `apps/api/app/routes/system.py` | **New** read-only `/api/v1/system/info` and `POST /api/v1/system/copilot/explain` (mock advisory; no secrets returned). |
| `apps/api/main.py` | Register the system router. |
| `docs/dashboard/DEMO_GUIDE.md` | **New** reviewer-facing dashboard guide. |
| `docs/evidence/phase10/dashboard-ux-hardening-report.md` | This report. |
| `docs/evidence/phase10/dashboard-ux/` | **New** screenshot index + 8 captures. |
| `scripts/demo/capture_phase10c2a_dashboard_ux.py` | **New** capture script (does not touch Phase 10A). |
| `README.md`, `docs/evidence/README.md`, `docs/evidence/phase10/README.md` | Index/link updates. |

---

## UI improvements

- Removed visible internal phase badges (Phase 5/5.5/6A/6B/7/8) from the cockpit UI;
  replaced with capability/product labels (Digital Twin, Robotics Lab, Mission
  Control, Observability & Reliability, Learning Evidence, On-demand, Optional
  profile, etc.). Phase history remains in docs.
- Added a top **Live Demo Cockpit** guide: watchlist, recommended demo flow with
  scroll-to-panel buttons, guided demo launcher, and a "prove it's not static HTML" card.
- Added a **Backend Proof** panel with live health, per-stream WebSocket counters,
  latest timestamps, trace/command/decision IDs, and copyable endpoint links.
- Added a **Capabilities & Profiles** matrix (active / artifact-only / mock /
  optional profile / offline-in-core) with activation commands.
- Added a global **System Event Timeline** (action log) with jump-to-panel links.
- Added an **Operator Copilot** panel (mode/provider/authority + on-demand mock explanation).
- Added toasts, panel pulse highlights, and "backend accepted, waiting for broadcast"
  feedback for twin commands.

---

## Button behavior map (summary)

See the full table in [docs/dashboard/DEMO_GUIDE.md](../../dashboard/DEMO_GUIDE.md#button-behavior-map).
Every visible button now: logs an action, shows a toast/receipt, pulses or scrolls
to the affected panel, and reports the honest backend result (`sent` / `backend` /
`rejected` / `unavailable` / `error`). No silent buttons remain. Robotics-lab live
commands are disabled while the bridge is offline; clearly-labeled local preview
buttons replace them.

---

## Backend proof features

- `/api/v1/system/info` returns non-secret runtime metadata (version, LLM mode,
  copilot authority, whether a real LLM key is configured — never the key itself).
- Backend proof panel surfaces counters and IDs sourced from live WebSocket/API responses.
- Direct, copyable endpoint links: `/health`, `/health/live`, `/health/ready`,
  `/telemetry/status`, `/model-scores/status`, `/mission/status`, `/status/services`,
  `/api/v1/system/info`, `/openapi.json`.

---

## Guided demo features

`▶ Start Guided Demo` opens an overlay that walks the 8-step flow (Backend Proof →
Mission Control → Failure Injection → HITL → Digital Twin → Learning Evidence →
Robotics Lab → Evidence Center), scrolling to and highlighting each panel. Next /
Previous / End, arrow keys, and Esc. No external libraries.

---

## Optional profile handling

- **Robotics Lab (Nav2 + SLAM):** offline in core. Live buttons disabled; offline
  reason + exact activation command (`docker compose --profile ros2-nav-slam up -d
  --build`) shown; local preview buttons animate the map (labeled UI-only). When the
  bridge is detected online via `/api/v1/nav-slam/status`, live buttons enable.
- **FL / RL / MLOps:** documented evidence mode with copy-run-command and
  copy-report-path actions; not claimed as always-on.
- **Real LLM:** optional; activation instructions shown; mock advisory copilot is
  the default and is backend-backed.

---

## Checks run

| Check | Result |
|-------|--------|
| `make lint` (ruff) | PASS |
| `.venv/bin/pytest tests/phase9/test_scan_claims.py -q` | PASS (6) |
| `.venv/bin/python scripts/scan_claims.py` (targeted + repo) | PASS |
| `bash scripts/verify_phase9.sh` | PASS (Block 1 + compose configs) |
| `ASSUME_UP=true bash scripts/demo/phase10a_verify_demo.sh` | PASS (0 critical, 0 warnings) |
| Dashboard manual + Playwright interaction (failure injection, twin, copilot, counters) | PASS |
| 8 UX screenshots captured | PASS |

---

## Claim safety

- Claim scanner passes; no medical/clinical/production-ready claims added.
- All new copy reinforces synthetic-only, advisory-only, no-clinical-use language.
- No raw restricted-term regex patterns embedded in docs.
- No real patient data, no secrets, no medical claims.

---

## Remaining risks

- ROS2/Nav2/SLAM remains offline in core (intentional); live runtime requires the
  `ros2-nav-slam` profile.
- FL/RL/MLOps remain on-demand; panels show idle/artifact defaults until run.
- Backend proof IDs depend on the agent loop producing decisions; in a fully nominal
  run a HITL gate may not open unless triggered (Low Confidence injection documented).
- Screenshots are section crops (not full-page), consistent with Phase 10A.

---

## What was explicitly NOT done

- No video / screen recording.
- No release, tag, or `v0`.
- No cloud / Kubernetes / VM.
- No frontend framework rewrite (vanilla JS/HTML/CSS retained).
- No fake live ROS2/Nav2/SLAM and no fake backend success.
- No mandatory real LLM dependency or external paid APIs.
- No medical/clinical or enterprise-production-ready claims.
- No changes to Phase 10A screenshot selectors or capture script.

---

## Final status

**PASS WITH DOCUMENTED RISKS** — interactive cockpit verified end-to-end on the core
profile; checks green; optional/offline boundaries are explicit and honest.
