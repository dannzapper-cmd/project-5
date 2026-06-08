"""Artifact and repo paths for Phase 8 mission control."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ARTIFACTS = ROOT / "artifacts"
PHASE8_DIR = ARTIFACTS / "phase8"
DOCS_EVIDENCE = ROOT / "docs" / "evidence"

MISSION_STATUS_ARTIFACT = PHASE8_DIR / "phase8_mission_status.json"
MISSION_TIMELINE_ARTIFACT = PHASE8_DIR / "phase8_mission_timeline.json"
MISSION_EVIDENCE_INDEX_ARTIFACT = PHASE8_DIR / "phase8_mission_evidence_index.json"
SCENARIO_SUMMARY_ARTIFACT = PHASE8_DIR / "phase8_scenario_summary.txt"

FL_ARTIFACTS = {
    "federated_report": ARTIFACTS / "learning" / "federated" / "federated_report.json",
    "federated_status": ARTIFACTS / "learning" / "federated" / "status.json",
    "federated_convergence": ARTIFACTS / "learning" / "federated" / "convergence.json",
    "federated_model_card": ARTIFACTS / "learning" / "federated" / "model_card_axon_fl_v1.md",
}

RL_ARTIFACTS = {
    "rl_report": ARTIFACTS / "learning" / "rl" / "rl_report.json",
}

RELIABILITY_ARTIFACTS = {
    "phase7a_report": ARTIFACTS / "reliability" / "phase7a_reliability_report.json",
    "failure_replay": ARTIFACTS / "reliability" / "failure_replay_report.json",
    "service_status_snapshot": ARTIFACTS / "reliability" / "service_status_snapshot.json",
}

OBSERVABILITY_ARTIFACTS = {
    "phase7b_report": ARTIFACTS / "observability" / "phase7b_observability_report.json",
    "metrics_snapshot": ARTIFACTS / "observability" / "metrics_snapshot.txt",
    "operational_status_snapshot": ARTIFACTS / "observability" / "operational_status_snapshot.json",
}
