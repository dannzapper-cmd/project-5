# ADR-013: Phase 8 — Integrated Mission Control System

## Status

Accepted

## Context

Phases 0–7 delivered AXON as a modular portfolio system: telemetry, edge inference,
agents/safety/HITL, digital twin, ROS2/Nav2/SLAM status, federated learning, RL,
and a lightweight observability/reliability layer. Each phase produced endpoints,
dashboard panels, scripts, and artifacts — but the operational loop was fragmented
across separate views.

Phase 8 integrates these layers into a **mission control cockpit**: a unified mission
API, deterministic scenario runner, internal Evidence Center index, mission timeline,
and a dashboard Mission Control section — without redesigning the entire dashboard or
adding heavy infrastructure.

## Decision

- **Mission API** under `/mission/*`:
  - `GET /mission/status` — unified component snapshot (artifact-backed, cached TTL 300s)
  - `GET /mission/timeline` — ordered operational loop events
  - `GET /mission/evidence` — honest Evidence Center index (file existence checks)
  - `GET /mission/scenarios` — scenario catalog
  - `POST /mission/scenarios/run` — deterministic offline scenario runner (seed 42)
- **Graceful degradation contract:** HTTP 200 for optional offline/missing artifacts;
  `degraded`, `degraded_components`, `limitations`, `synthetic_data_only`,
  `no_medical_claims` on all mission responses.
- **Scenario runner:** `scripts/run_phase8_mission_scenario.py` + shared module
  `apps/api/app/mission/scenarios.py`; artifacts under `artifacts/phase8/`.
- **Dashboard:** new static HTML/JS/CSS Mission Control section; 10s polling; fallback
  when Mission API unavailable.
- **Verification:** `scripts/verify_phase8.sh`, `tests/phase8/`, banned-term scan.

## Consequences

- AXON presents as a coherent end-to-end simulated operational loop in one view.
- No new Docker services, profiles, or PyPI/npm dependencies.
- Existing endpoints and schemas remain untouched; one new router registration added.
- Historical FL/RL/Phase 7 artifacts connect honestly — missing files reported as
  `missing`, not invented.

## Not Doing

- **Phase 9** final QA/hardening/repair (next step after merge).
- **Phase 10** packaging, portfolio README, release notes, demo video, screenshots.
- **Cloud**, **Kubernetes**, or mandatory **VM** workflow.
- **Dashboard redesign** — additive Mission Control section only.
- **New technology stack** (no React, no bundler, no OTEL/Prometheus mandate).
- **Real patient/clinical data** or **medical claims**.
- **Heavy FL/RL retraining** or mandatory live ROS2/Nav2/SLAM runtime for success.
