# AXON — Claims and Positioning Guide

Quick reference for presentations, README edits, and portfolio copy. Prevents scope inflation.

---

## Positioning statement

**AXON is a synthetic, local-first Bio-Robotics Edge Command System for simulated rehab robot operations.** It demonstrates intelligent systems engineering with evidence — not clinical care, care-environment rollout, or medical device certification.

---

## Safe language (use freely)

| Term | Meaning in AXON |
|------|-----------------|
| Simulated / synthetic-only | All biomedical-inspired signals are generated or replayed |
| Local-first | Docker Compose on developer machine; no required cloud |
| Edge-like inference | ONNX Runtime in local stack; not deployed clinical edge hardware |
| Safety-aware | Rules, envelopes, HITL — not autonomous clinical authority |
| Human-in-the-loop | Explicit confirmation for high-risk / low-confidence paths |
| Compose-validated | `docker compose config` passes; live runtime may be offline |
| On-demand | FL, RL, MLflow, Nav2 require explicit profile or script |
| Synthetic retraining / candidate refresh | Classical MLOps loop for small models |
| Evidence-backed | Screenshots, scripts, reports with reproducible commands |
| PASS WITH DOCUMENTED RISKS | Success with listed limitations — not hidden failures |

---

## Claims We Avoid

Do **not** say or imply:

- Medical-grade monitoring
- Diagnosis of arrhythmia, fatigue, SpO2 problems, or any clinical condition
- Treatment or prevention advice
- Production-ready medical device
- Hospital / clinic deployment
- Autonomous clinical decision-maker
- Real patient monitoring or real patient data
- Fine-tuning of a pretrained neural network (use synthetic retraining / candidate refresh)
- ROS2/Nav2/SLAM always live when only core profile runs
- FL/RL/MLOps always running in core demo
- Enterprise healthcare compliance (FDA, HIPAA) unless explicitly negated as out of scope

---

## Allowed negations (keep these)

Phrases like "not a medical device", "does not diagnose", "no real patient data", and "not for clinical use" are **required disclaimers**, not violations. The claim scanner (`scripts/scan_claims.py`) skips dedicated "Claims We Avoid" sections and honors negation qualifiers.

---

## Profile honesty cheat sheet

| Subsystem | Core demo | To show live |
|-----------|-----------|--------------|
| Telemetry + inference | Live | `core` profile |
| Agents + HITL | Live | `core` profile |
| Digital twin | Live | `core` profile |
| Mission / evidence index | Live (partial artifacts) | `core` + local generation |
| MLOps artifacts | Often idle / not_generated | `make mlops-pipeline`, `learning` profile |
| FL / RL panels | Artifact-only | `make learning-fl-run`, `make learning-rl-run` |
| ROS2 bridge | Offline in core | `--profile ros2` |
| Nav2 / SLAM MiniLab | Offline panel in core | `--profile ros2-nav-slam` |

---

## Evidence before claims

Before stating a capability in public copy:

1. Check [phase9_capability_truth_matrix.md](../evidence/phase9_capability_truth_matrix.md)
2. Link Phase 10A screenshots or runbook commands where visual proof exists
3. Run `scripts/scan_claims.py` on changed markdown
4. Record limitations in verification reports — do not bury them

---

*Enforced in CI via `scripts/verify_phase9.sh` and `tests/phase9/test_scan_claims.py`*
