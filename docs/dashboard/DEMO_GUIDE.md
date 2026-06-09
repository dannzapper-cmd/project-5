# AXON Dashboard Demo Guide

A reviewer-facing guide to the AXON dashboard (the **Live Operations Cockpit**).
It explains how to verify the dashboard is connected to a live backend, what each
panel means, how every button behaves, and where the optional/profile-gated
boundaries are. You should not need to read the whole repository to understand the UI.

> Synthetic data only. Not a medical device. No clinical use. The operator copilot
> is advisory only and cannot authorize critical actions.

---

## Dashboard overview

Open the dashboard at <http://localhost:3000> after starting the core profile:

```bash
make models-generate
docker compose --profile core up -d --build
```

The dashboard polls the API at `http://localhost:8000` and subscribes to eight
WebSocket streams. It is a single-page operations cockpit organized top-to-bottom as:

1. **Live Demo Cockpit** — what to watch, recommended flow, guided demo, and the
   "how to prove this is not static HTML" card.
2. **Backend Proof / Live System Proof** — live health, WebSocket counters,
   timestamps, IDs, and direct endpoint links.
3. **Capabilities & Profiles** — what is live in core, artifact-backed, or
   optional-profile.
4. **System Event Timeline** — every action and important backend response.
5. Operational panels — Connection Status, Observability & Reliability, Mission
   Control, Safety Panel, HITL / Safety Gate, Operator Copilot, Failure Injection,
   Edge AI, Live Telemetry, Live Model Scores, Agent Traces, Decision Timeline,
   Learning Evidence (FL / RL / MLOps), Digital Twin, Robotics Lab (Nav2 + SLAM).

---

## How to verify the dashboard is live

The dashboard is **not static HTML**. To prove it independently:

- Watch the **Backend Proof** panel: the WebSocket counters (sensor events, model
  scores, agent traces, decisions, safety updates, twin updates) increase over time,
  and the "Last telemetry / Last model score" timestamps advance.
- The header badge shows **Backend: live** when `/health` responds.
- Open any endpoint link in the Backend Proof panel in a new tab; the counters and
  IDs on the page come from those same responses:
  - `/health`, `/health/live`, `/health/ready`
  - `/telemetry/status`, `/model-scores/status`, `/mission/status`
  - `/status/services`, `/api/v1/system/info`, `/openapi.json`
- Or run the verification script (copy button provided in the cockpit):

```bash
ASSUME_UP=true bash scripts/demo/phase10a_verify_demo.sh
```

---

## Recommended 3-minute demo path

Use the **Recommended demo flow** buttons (they scroll to and highlight each panel),
or click **▶ Start Guided Demo** for a guided overlay.

1. **Backend Proof** — counters and timestamps moving; open `/health`.
2. **Mission Control** — run a scenario; watch the timeline update.
3. **Failure Injection** — click **Low Confidence**; watch Safety Panel + timeline react.
4. **HITL / Safety** — confirm or reject a pending gate (if opened); see the receipt.
5. **Digital Twin** — Pause / Resume / Set Assist Mode; see the command receipt.
6. **Learning Evidence** — copy a run command or report path (artifact-backed).
7. **Robotics Lab** — explain the offline boundary; run a local preview; copy the activation command.
8. **Evidence Center** — show the evidence index counts.

---

## What each panel means

| Panel | Meaning |
|-------|---------|
| Backend Proof | Live API/WS connectivity, counters, timestamps, latest trace/command/decision IDs, endpoint links. |
| Capabilities & Profiles | Per-capability status (active / artifact-only / optional profile / mock) and how to activate. |
| System Event Timeline | Append-only action log: timestamp, action, module, result, detail, jump link. |
| Connection Status | WebSocket dots and raw sensor/model counters. |
| Observability & Reliability | `/health/live`, `/health/ready`, `/status/services` component table. |
| Mission Control | Operational loop status, timeline, evidence preview, scenario runner. |
| Safety Panel | Live safety verdict and the active failure mode badge. |
| HITL / Safety Gate | Pending decision, reason, risk/confidence, Confirm/Reject, last receipt. |
| Operator Copilot | LLM mode/provider/model, advisory authority, on-demand mock explanation. |
| Failure Injection | Inject controlled faults; visibly changes safety state. |
| Edge AI / Telemetry / Model Scores | Live ONNX scores and synthetic signal streams. |
| Agent Traces / Decision Timeline | LangGraph trace and decision history. |
| Learning Evidence | FL / RL / MLOps on-demand evidence with copy/report actions. |
| Digital Twin | SVG state mirror with safe command API. |
| Robotics Lab (Nav2 + SLAM) | Offline in core; activation command + local preview. |

---

## Button behavior map

| Button | Backend route | Visible effect | Affected panel | Unavailable when |
|--------|---------------|----------------|----------------|------------------|
| Confirm Decision | `POST /api/v1/decisions/{id}/confirm` | Receipt + log + toast; gate cleared | HITL / Safety | No pending gate (disabled) |
| Reject Decision | `POST /api/v1/decisions/{id}/reject` | Receipt + log + toast; gate cleared | HITL / Safety | No pending gate (disabled) |
| Sensor Dropout | `POST /api/v1/failure-injection/sensor_dropout` | Safety + failure badge + log | Failure / Safety | API unreachable |
| Corrupt Event | `POST /api/v1/failure-injection/corrupt_event` | Safety + failure badge + log | Failure / Safety | API unreachable |
| Low Confidence | `POST /api/v1/failure-injection/model_low_confidence` | Safety + may open HITL gate | Failure / Safety / HITL | API unreachable |
| Stale Telemetry | `POST /api/v1/failure-injection/stale_telemetry` | Safety + failure badge + log | Failure / Safety | API unreachable |
| Reset (injection) | `POST /api/v1/failure-injection/reset` | Clears active failure | Failure / Safety | API unreachable |
| Twin: Pause / Resume / Safety Stop | `POST /api/v1/twin/command` | Receipt + "waiting for broadcast" then state update | Digital Twin | API unreachable |
| Set Assist Mode | `POST /api/v1/twin/command` | Receipt + log | Digital Twin | API unreachable |
| Generate explanation | `POST /api/v1/system/copilot/explain` | Mock advisory text + trace ID | Operator Copilot | API unreachable |
| Mission scenario buttons | `POST /mission/scenarios/run` | Timeline + result + log | Mission Control | API unreachable |
| MLOps dry-run | `POST /api/v1/mlops/promote-candidate` | Review record id (no promotion) | MLOps Evidence | API unavailable |
| Start Mapping / Send Nav Goal / Blocked Goal / Reset | `POST /api/v1/nav-slam/command` | Receipt | Robotics Lab | **Disabled** when bridge offline (core) |
| Preview Mapping / Nav Goal / Blocked / Reset | none (local UI) | Animated SVG preview, labeled local-only | Robotics Lab | always available |
| Copy / Copy run command / Copy report path | none (clipboard) | Toast + log | various | — |
| Flow steps / Jump → / Start Guided Demo | none (scroll) | Scroll + highlight | target panel | — |

---

## Backend proof and action receipts

Every button click appends an entry to the **System Event Timeline** with a result
state: `sent`, `backend` (backend accepted/responded), `rejected`, `unavailable`
(e.g. local-only preview), or `error`. Where the backend returns an identifier
(trace ID, command ID, decision ID, run ID), it is surfaced in the Backend Proof
panel. The dashboard does **not** fabricate backend confirmation — if the API
returns an error or is unreachable, that is what the log and toast show.

---

## Guided demo mode

Click **▶ Start Guided Demo**. An overlay walks through the eight flow steps with
short explanations, scrolling to and highlighting each panel. Use **Next** /
**Previous** / **End demo**, or the arrow keys / **Esc**. No external libraries.

---

## Failure injection flow

1. Click **Low Confidence** in Failure Injection.
2. The Safety Panel shows `Low confidence: true` and the **Active failure mode**
   badge changes; both panels pulse.
3. The System Event Timeline logs the injection and the safety update.
4. If the agent loop opens a HITL gate, the **HITL / Safety Gate** panel enables
   Confirm / Reject.
5. Click **Reset** to clear the active failure.

---

## HITL flow

- When no gate is pending, the panel reads "No pending HITL gate" and explains how
  to trigger one (Low Confidence injection).
- When pending, the panel shows the decision ID, reason, and risk/confidence, and
  enables Confirm / Reject.
- Confirm / Reject call the backend, show a receipt, clear the gate, and log the action.

---

## Digital Twin commands

Pause, Resume, Safety Stop, and Set Assist Mode send `POST /api/v1/twin/command`.
The command returns a receipt (status + reason + trace) and the panel shows
"Backend accepted — waiting for next twin broadcast"; when the next twin broadcast
arrives with the new mode, the panel pulses and logs the state change. Twin motion
is simulated only — no real hardware.

---

## LLM / Copilot mode

The Operator Copilot panel shows the live LLM mode/provider/model from
`/api/v1/system/info`. The default core demo uses a **deterministic offline mock**
(`mock-operator-copilot-v1`) — no API key required, no clinical inference. Click
**Generate explanation** to call `POST /api/v1/system/copilot/explain`; it returns
an advisory summary grounded on the current safety/decision state plus a trace ID.

A **real** LLM is optional and never required for the demo. To enable it, set
`AXON_LLM_MODE=real`, `AXON_LLM_PROVIDER` (openai/anthropic/google), and the matching
API key on the `api` service, then restart core. The copilot remains advisory only.

---

## Learning evidence mode

FL, RL, and MLOps are **documented evidence mode** — they run on demand and are not
always-on in core. Each panel shows idle/artifact defaults plus actions to copy the
exact run command and report path:

```bash
make learning-fl-run     # Federated learning (Flower FedAvg)
make learning-rl-run     # RL micro-module (Gymnasium PPO)
make mlops-pipeline      # Synthetic retraining / candidate refresh
# or: docker compose --profile learning up --build
```

---

## Robotics / Nav2 / SLAM profile boundary

The Robotics Lab (Nav2 + SLAM MiniLab) is **offline in the core demo** by design,
for reproducibility and resource control. The panel:

- shows an offline reason and the exact activation command;
- **disables** the live MiniLab command buttons while the bridge is offline;
- provides clearly-labeled **local preview** buttons (UI-only animations, not live ROS2).

Activate the live lab with:

```bash
docker compose --profile ros2-nav-slam up -d --build
```

When the bridge is detected online (via `/api/v1/nav-slam/status`), the live command
buttons enable automatically and return backend receipts.

---

## Capabilities & profiles

The Capabilities & Profiles panel summarizes each capability as **active**,
**artifact-only**, **mock (advisory)**, **optional profile**, or **offline in core**,
with the activation command. See also [docs/architecture/profiles.md](../architecture/profiles.md).

---

## What this dashboard does not prove

- It does **not** prove medical or clinical capability — all signals are synthetic.
- It does **not** prove enterprise production readiness (see
  [docs/production/README.md](../production/README.md)).
- It does **not** run live ROS2/Nav2/SLAM in the core profile.
- It does **not** train FL/RL/MLOps in core — those are on-demand.
- The copilot does **not** make decisions or authorize actions.

---

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Header shows "Backend: offline" | API not running — `docker compose --profile core up -d`. |
| Counters stuck at 0 | Sensor generators/edge inference warming up; wait ~30–60s. |
| Live MiniLab buttons disabled | Expected in core — start `ros2-nav-slam` profile or use Preview buttons. |
| FL/RL/MLOps show idle | Expected — run the on-demand commands above. |
| Copilot says "unavailable" | API unreachable — check `/health`. |

---

## Related evidence

- [Dashboard UX hardening report](../evidence/phase10/dashboard-ux-hardening-report.md)
- [Dashboard UX screenshot index](../evidence/phase10/dashboard-ux/screenshot-index.md)
- [Phase 10A demo evidence](../evidence/phase10/demo/)
- [Fresh clone checklist](../evidence/phase10/demo/fresh-clone-demo-checklist.md)
- [Execution profiles](../architecture/profiles.md)
- [Evidence Center index](../evidence/README.md)
