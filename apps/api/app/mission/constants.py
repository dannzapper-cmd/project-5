"""Phase 8 mission control constants."""

from __future__ import annotations

STATUS_TTL_S = 300
EVIDENCE_TTL_S = 300
DEFAULT_SEED = 42
PHASE = "phase_8"

SCENARIO_NAMES = (
    "normal_operation",
    "anomaly_safety_intervention",
    "learning_evidence_review",
)

TIMELINE_STAGES = (
    "telemetry_received",
    "edge_inference_scored",
    "anomaly_status_evaluated",
    "agent_decision_generated",
    "hitl_safety_gate_checked",
    "digital_twin_updated",
    "ros2_status_checked",
    "nav_slam_status_checked",
    "fl_evidence_loaded",
    "rl_evidence_loaded",
    "observability_checked",
    "reliability_checked",
    "evidence_artifact_written",
)
