# Phase 9 Capability Truth Matrix

Generated: 2026-06-08 | Branch: `feat/phase-9-final-integrity-seal`

Columns: **Claimed** (docs/README), **Impl** (code exists), **Wired** (compose/API/dashboard), **Tested** (automated tests), **Evidenced** (artifacts/docs), **Verified P9** (checked this pass), **Status** (honest summary).

| Capability | Claimed | Files | Impl | Wired | Tested | Evidenced | Verified P9 | Status |
|------------|---------|-------|------|-------|--------|-----------|---------------|--------|
| Telemetry spine (MQTT→API→Redis→WS) | Yes | `apps/api/`, `services/sensor-generators/`, `replay/` | Yes | Yes (core profile) | Yes | Yes | Yes | **Working** — Phase 1 regression in test suite |
| ONNX edge inference | Yes | `services/edge-inference/`, `models/onnx/` | Yes | Yes (core) | Yes | Yes | Yes | **Working** — smoke/benchmark scripts |
| Sensor fusion (standalone) | Partial | `services/fusion-service/` | Placeholder | No | No | README only | Yes | **Thin/placeholder** — not implemented |
| Sensor fusion (twin aggregate) | Implicit | `apps/api/app/twin/service.py` | Partial | Yes (twin API/WS) | Yes | Twin schema | Yes | **Partial** — mean-confidence fusion in twin only |
| LangGraph agents + HITL | Yes | `apps/api/app/agents/` | Yes | Yes | Yes | Phase 3 docs | Yes | **Working** — not modified in P9 |
| Safety envelope | Yes | `apps/api/app/safety/`, `docs/safety/` | Yes | Yes | Yes | Yes | Yes | **Working** |
| MLOps synthetic retraining | Yes | `apps/mlops/`, `scripts/run_mlops_pipeline.py` | Yes | Yes (API/dashboard) | Yes | On-demand artifacts | Yes | **Working (smoke)** — honest labels; paths fixed in evidence index |
| Drift detection → retrain recommend | Yes | `apps/mlops/drift.py`, `apps/api/app/mlops/drift_watcher.py` | Yes | Yes (API status) | Yes | `docs/evidence/drift-and-continual-learning.md` | Yes | **Working** — recommends `evaluate_candidate_model` → `make mlops-pipeline` |
| Digital twin mirror | Yes | `apps/api/app/twin/` | Yes | Yes | Yes | Phase 5 docs | Yes | **Working** |
| ROS2 bridge (thin) | Yes | `services/ros2-bridge/` | Yes | Yes (ros2 profile) | Partial | Phase 5 docs | Yes (config) | **Compose-validated** — live runtime not gated |
| Nav2 + SLAM MiniLab | Yes | `services/ros2-nav-slam-minilab/` | Yes | Yes (ros2-nav-slam) | Partial | ADR-009/010 | Yes (config) | **Compose-validated** — headless lab; not run in CI |
| Federated learning (Flower) | Yes | `apps/learning/federated/`, `scripts/run_federated_learning.py` | Yes | Yes (learning profile) | Yes | On-demand JSON | Yes | **Working (on-demand)** |
| RL micro-module (PPO) | Yes | `apps/learning/rl/`, `scripts/run_rl_micro_module.py` | Yes | Yes (learning profile) | Yes | On-demand JSON | Yes | **Working (on-demand)** |
| Observability (lightweight) | Yes | `apps/api/app/observability/`, `scripts/observability/` | Yes | Yes (obs profile) | Yes | Committed snapshots | Yes | **Working** |
| Reliability (health/ready) | Yes | `apps/api/app/reliability/` | Yes | Yes | Yes | Committed snapshots | Yes | **Working** |
| Mission control API | Yes | `apps/api/app/mission/`, `apps/api/app/routes/mission.py` | Yes | Yes | Yes | Runtime-generated locally, ignored | Yes | **Working** — honest degradation; scenario JSONs are not committed source truth |
| Evidence Center index | Yes | `apps/api/app/mission/evidence_index.py` | Yes | Yes | Yes | API + docs | Yes | **Working** — existence checks truthful after path fix |
| Dashboard mission panel | Yes | `apps/dashboard/` | Yes | Yes | Partial | Manual | Yes | **Working** — static HTML/JS polling |
| Phase 9 verification gate | Yes | `scripts/verify_phase9.sh`, `scripts/scan_claims.py` | Yes | Yes (Makefile/CI) | Yes | This report + Final Seal report | Yes | **Working** — lightweight default with runtime artifact hygiene checks |
| Cloud/Kubernetes deploy | No (deferred) | — | No | No | No | No | Yes | **Not implemented** — Phase 10+ optional |
| Portfolio packaging / video | No | — | No | No | No | No | Yes | **Not started** — Phase 10 |

## Status legend

- **Working** — code + tests pass; scope matches claim
- **Working (on-demand)** — requires explicit profile/make target
- **Working (smoke)** — CI-friendly smoke path verified; full training optional
- **Partial** — subset implemented; claim must stay qualified
- **Thin/placeholder** — docs/skeleton only
- **Compose-validated** — config parses; runtime not required in Phase 9
- **Not implemented** — explicitly deferred

## P9 verification methods used

- documented install path: `201 passed, 4 skipped`
- full local extras venv: `make test` (`235 passed`)
- `bash scripts/verify_phase9.sh`
- Static review of fusion, MLOps paths, evidence index, dashboard labels
- Docker Compose config for all listed profiles
