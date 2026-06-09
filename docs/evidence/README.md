# Evidence Center

AXON's proof-of-capability archive. Every major technology produces visible, reproducible evidence — or an honest `not_generated` / placeholder state.

---

## Purpose

- Portfolio demonstrations with verifiable artifacts
- Interview and review narratives grounded in commands, not adjectives
- Regression baselines for performance, safety, and claim integrity
- Phase completion checkpoints with documented risks

---

## Phase index

| Phase | Focus | Key artifacts |
|-------|-------|-----------------|
| 0–2 | Contracts, telemetry, edge inference | [evidence-checklist.md](evidence-checklist.md), [phase2-inference-benchmark.md](phase2-inference-benchmark.md) |
| 3 | Agents, safety, HITL | [phase-3-agents-safety.md](phase-3-agents-safety.md), [phase-3-agent-graph.md](phase-3-agent-graph.md) |
| 4 | MLOps synthetic retraining | [phase-4-mlops.md](phase-4-mlops.md), [phase-4-verification.md](phase-4-verification.md) |
| 5 | Digital twin, ROS2 | [phase-5-digital-twin-ros2.md](phase-5-digital-twin-ros2.md) |
| 5.5 | Nav2 + SLAM MiniLab | [phase-5-5-nav2-slam-minilab.md](phase-5-5-nav2-slam-minilab.md) |
| 6A / 6B | FL, RL on-demand | [phase-6a-federated-learning.md](phase-6a-federated-learning.md), [phase-6b-rl-micro-module.md](phase-6b-rl-micro-module.md) |
| 7 | Observability, reliability | `artifacts/observability/`, `artifacts/reliability/` (curated snapshots) |
| 8 | Mission control | [phase8_snapshot_note.md](phase8_snapshot_note.md) — runtime scenario JSONs generated locally, not committed |
| 9 | QA, integrity seal | [phase9_final_seal_report.md](phase9_final_seal_report.md), [phase9_verification_report.md](phase9_verification_report.md), [phase9_capability_truth_matrix.md](phase9_capability_truth_matrix.md) |
| 10A | Demo automation + screenshots | [phase10/demo/](phase10/demo/) — **PASS WITH DOCUMENTED RISKS** |
| 10B | Portfolio packaging | [phase10/packaging-report.md](phase10/packaging-report.md) |

---

## Phase 10A demo evidence (primary visual proof)

| Artifact | Path |
|----------|------|
| Folder README | [phase10/demo/README.md](phase10/demo/README.md) |
| Screenshot index | [phase10/demo/screenshot-index.md](phase10/demo/screenshot-index.md) |
| Demo verification report | [phase10/demo/demo-verification-report.md](phase10/demo/demo-verification-report.md) |
| Runbook | [phase10/demo/runbook-phase10a.md](phase10/demo/runbook-phase10a.md) |
| Commands summary | [phase10/demo/commands-summary.md](phase10/demo/commands-summary.md) |
| Latest screenshots | [phase10/demo/screenshots/latest/](phase10/demo/screenshots/latest/) |
| Capture metadata | [phase10/demo/screenshots/20260609-054740/capture-metadata.json](phase10/demo/screenshots/20260609-054740/capture-metadata.json) |

**Reproduce core demo:**

```bash
make models-generate
docker compose --profile core up -d --build
ASSUME_UP=true bash scripts/demo/phase10a_verify_demo.sh
.venv/bin/python scripts/demo/capture_phase10a_screenshots.py   # optional re-capture
.venv/bin/python scripts/demo/validate_phase10a_screenshots.py
```

---

## Model and data cards

| Card | Path |
|------|------|
| EMG candidate model | [model-card-emg-v2-candidate.md](model-card-emg-v2-candidate.md) |
| IMU candidate model | [model-card-imu-v2-candidate.md](model-card-imu-v2-candidate.md) |
| Synthetic replay data | [data-card-synthetic-replay.md](data-card-synthetic-replay.md) |
| Drift / continual learning | [drift-and-continual-learning.md](drift-and-continual-learning.md) |
| Candidate promotion | [candidate-promotion-workflow.md](candidate-promotion-workflow.md) |

---

## Claim scan and QA

| Tool | Purpose |
|------|---------|
| `scripts/scan_claims.py` | Line-level unsafe medical/device claim detection |
| `scripts/verify_phase9.sh` | Evidence index, hygiene, compose-config, claim gate |
| `tests/phase9/test_scan_claims.py` | Regression tests for claim scanner negation handling |

---

## ADRs

Architecture decisions: [../adr/](../adr/) — link evidence to ADRs when capabilities depend on explicit scope choices (e.g. Nav2 MiniLab ADR-009/010).

---

## Known risks (carried forward)

Documented in Phase 9 and 10A reports — not hidden:

- ROS2/Nav2/SLAM **offline** in core-only demo; compose-validated unless `ros2-nav-slam` started
- FL/RL/MLOps artifacts **on-demand**; dashboard may show idle or `not_generated`
- ONNX models **gitignored** — `make models-generate` required on fresh clone
- Standalone `fusion-service` is a **placeholder**; twin-side aggregation only
- Phase 10A status: **PASS WITH DOCUMENTED RISKS**

---

## Rules

1. Mark evidence with phase number and date
2. Do not claim evidence for unimplemented features
3. Prefer reproducible commands over one-off screenshots
4. Do not commit runtime-generated scenario JSONs as source truth
5. Link evidence to model/data cards and ADRs when relevant

Full checklist: [evidence-checklist.md](evidence-checklist.md)

---

## Portfolio packaging (Phase 10B)

Written packaging for external presentation:

- [../portfolio/AXON_CASE_STUDY.md](../portfolio/AXON_CASE_STUDY.md)
- [../portfolio/PORTFOLIO_COPY.md](../portfolio/PORTFOLIO_COPY.md)
- [../portfolio/TECHNICAL_QA.md](../portfolio/TECHNICAL_QA.md)
- [../portfolio/CLAIMS_AND_POSITIONING.md](../portfolio/CLAIMS_AND_POSITIONING.md)

## Business documentation

Product and business analysis (non-clinical, non-hiring):

- [../business/AXON_BUSINESS_CASE.md](../business/AXON_BUSINESS_CASE.md)
- [phase10/business-case-audit-report.md](phase10/business-case-audit-report.md)

## Production documentation (planning only)

Enterprise architecture and production-readiness roadmap. AXON is **not** enterprise-production-ready today.

- [../production/README.md](../production/README.md)
- [../production/ENTERPRISE_PRODUCTION_PATH.md](../production/ENTERPRISE_PRODUCTION_PATH.md)
- [phase10/production-path-report.md](phase10/production-path-report.md)
