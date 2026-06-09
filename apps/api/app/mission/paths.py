"""Artifact and repo paths for Phase 8 mission control."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ARTIFACTS = ROOT / "artifacts"
DOCS_EVIDENCE = ROOT / "docs" / "evidence"


def _resolve_phase8_dir() -> Path:
    override = os.environ.get("AXON_PHASE8_ARTIFACT_DIR")
    if override:
        return Path(override)
    return ARTIFACTS / "phase8"


PHASE8_DIR = _resolve_phase8_dir()

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

MLOPS_ARTIFACTS = {
    "metrics": ARTIFACTS / "mlops" / "latest_eval" / "metrics.json",
    "eval_report": ARTIFACTS / "mlops" / "latest_eval" / "eval_report.json",
    "candidate_manifest": ARTIFACTS / "mlops" / "registry" / "candidate_manifest.json",
}

MLOPS_DOC_ARTIFACTS = {
    "model_card_emg": DOCS_EVIDENCE / "model-card-emg-v2-candidate.md",
    "model_card_imu": DOCS_EVIDENCE / "model-card-imu-v2-candidate.md",
    "data_card": DOCS_EVIDENCE / "data-card-synthetic-replay.md",
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

GENERATE_CMDS = {
    "federated_learning": "make learning-fl-run",
    "reinforcement_learning": "make learning-rl-run",
    "mlops": "make mlops-pipeline",
    "mission_scenario": "bash scripts/verify_phase8.sh",
}
