"""Phase 8 deterministic mission scenario runner."""

from __future__ import annotations

import json
import random
import subprocess
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from apps.api.app.mission.constants import DEFAULT_SEED, PHASE, SCENARIO_NAMES
from apps.api.app.mission.evidence_index import build_evidence_index
from apps.api.app.mission.paths import (
    MISSION_EVIDENCE_INDEX_ARTIFACT,
    MISSION_STATUS_ARTIFACT,
    MISSION_TIMELINE_ARTIFACT,
    PHASE8_DIR,
    SCENARIO_SUMMARY_ARTIFACT,
)
from apps.api.app.mission.status import build_mission_status

REQUIRED_ARTIFACT_FIELDS = (
    "synthetic_data_only",
    "no_medical_claims",
    "run_id",
    "generated_at",
    "scenario",
    "limitations",
    "seed",
)


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def _seed_rng() -> random.Random:
    return random.Random(DEFAULT_SEED)


def _synthetic_telemetry(rng: random.Random) -> dict[str, float]:
    return {
        "emg": round(rng.uniform(0.2, 0.8), 4),
        "ecg_like": round(rng.uniform(0.4, 0.9), 4),
        "imu": round(rng.uniform(0.1, 0.6), 4),
        "spo2_proxy": round(rng.uniform(0.85, 0.99), 4),
        "robot_state": round(rng.uniform(0.0, 1.0), 4),
    }


def _timeline_event(
    *,
    stage: str,
    title: str,
    summary: str,
    source_component: str,
    status: str,
    offset_s: int,
    base: datetime,
    trace_id: str,
    artifact_ref: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "timestamp": (base.replace(microsecond=0) + timedelta(seconds=offset_s)).isoformat(),
        "stage": stage,
        "title": title,
        "summary": summary,
        "source_component": source_component,
        "status": status,
        "trace_id": trace_id,
        "artifact_ref": artifact_ref,
        "details": details or {},
    }


def _build_scenario_timeline(
    scenario: str,
    *,
    trace_id: str,
    run_id: str,
    anomaly: bool = False,
) -> list[dict[str, Any]]:
    base = datetime.now(tz=UTC)
    rng = _seed_rng()
    telemetry = _synthetic_telemetry(rng)

    if anomaly:
        telemetry["emg"] = 0.97
        telemetry["imu"] = 0.92

    stages: list[tuple[str, str, str, str, str]] = [
        (
            "telemetry_received",
            "Synthetic telemetry received",
            "MQTT/Redis synthetic ingest",
            "telemetry",
            "ok",
        ),
        (
            "edge_inference_scored",
            "Edge inference scored synthetic signals",
            "ONNX Runtime edge inference",
            "edge_inference",
            "ok",
        ),
        (
            "anomaly_status_evaluated",
            "Anomaly fusion evaluated",
            "Safety fusion layer",
            "anomaly_safety",
            "warning" if anomaly else "ok",
        ),
        (
            "agent_decision_generated",
            "Agent decision generated",
            "LangGraph operational decision",
            "agents",
            "ok",
        ),
        (
            "hitl_safety_gate_checked",
            "HITL safety gate checked",
            "Human-in-the-loop gate",
            "safety_hitl",
            "blocked" if anomaly else "ok",
        ),
        (
            "digital_twin_updated",
            "Digital twin state updated",
            "Twin mirror from streams",
            "digital_twin",
            "simulated",
        ),
        (
            "ros2_status_checked",
            "ROS2 bridge status checked",
            "ROS2 thin adapter",
            "ros2",
            "skipped",
        ),
        (
            "nav_slam_status_checked",
            "Nav2/SLAM status checked",
            "Nav2 SLAM MiniLab",
            "nav_slam",
            "skipped",
        ),
        (
            "fl_evidence_loaded",
            "Federated learning evidence loaded",
            "FL artifacts",
            "federated_learning",
            "simulated",
        ),
        (
            "rl_evidence_loaded",
            "RL evidence loaded",
            "RL artifacts",
            "reinforcement_learning",
            "simulated",
        ),
        (
            "observability_checked",
            "Observability status checked",
            "Phase 7 observability",
            "observability",
            "ok",
        ),
        (
            "reliability_checked",
            "Reliability status checked",
            "Phase 7 reliability",
            "reliability",
            "ok",
        ),
        (
            "evidence_artifact_written",
            "Phase 8 evidence artifacts written",
            "Mission scenario runner",
            "mission_scenario",
            "ok",
        ),
    ]

    if scenario == "learning_evidence_review":
        for i, row in enumerate(stages):
            stage = row[0]
            if stage in ("fl_evidence_loaded", "rl_evidence_loaded"):
                stages[i] = (stage, row[1], row[2], row[3], "ok")
            elif stage in (
                "telemetry_received",
                "edge_inference_scored",
                "agent_decision_generated",
            ):
                stages[i] = (stage, row[1], row[2], row[3], "skipped")

    events: list[dict[str, Any]] = []
    for idx, (stage, title, summary, source, status) in enumerate(stages):
        details: dict[str, Any] = {"seed": DEFAULT_SEED, "telemetry": telemetry}
        if status == "skipped":
            details["reason"] = "Scenario focuses on learning evidence — runtime stage skipped"
        if stage == "ros2_status_checked":
            details["reason"] = "No live ROS2 runtime required for Phase 8"
        if stage == "nav_slam_status_checked":
            details["reason"] = "Nav2/SLAM MiniLab optional profile offline"
        events.append(
            _timeline_event(
                stage=stage,
                title=title,
                summary=summary,
                source_component=source,
                status=status,
                offset_s=idx,
                base=base,
                trace_id=trace_id,
                artifact_ref=f"artifacts/phase8/phase8_scenario_{scenario}_{run_id}.json"
                if stage == "evidence_artifact_written"
                else None,
                details=details,
            )
        )

    return events


def _scenario_limitations(scenario: str) -> list[str]:
    base = [
        "Synthetic operational simulation only — no real hardware or biomedical data",
        "ROS2/Nav2/SLAM stages skipped when optional profiles are offline",
        "Evidence loaded from existing artifacts without retraining",
    ]
    if scenario == "anomaly_safety_intervention":
        base.append("Anomaly path demonstrates safety/HITL gate — not a real alert system")
    if scenario == "learning_evidence_review":
        base.append("Runtime pipeline stages skipped to focus on FL/RL evidence connectivity")
    return base


def _components_touched(scenario: str) -> list[str]:
    common = [
        "telemetry",
        "edge_inference",
        "anomaly_safety",
        "agents",
        "safety_hitl",
        "digital_twin",
        "observability",
        "reliability",
        "evidence_center",
    ]
    if scenario == "learning_evidence_review":
        return [
            "federated_learning",
            "reinforcement_learning",
            "evidence_center",
            "mission_control",
        ]
    if scenario == "anomaly_safety_intervention":
        return common + ["safety_hitl"]
    return common


def validate_artifact_payload(payload: dict[str, Any], *, label: str) -> None:
    missing = [field for field in REQUIRED_ARTIFACT_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"{label} missing required fields: {missing}")
    if payload["synthetic_data_only"] is not True:
        raise ValueError(f"{label}: synthetic_data_only must be true")
    if payload["no_medical_claims"] is not True:
        raise ValueError(f"{label}: no_medical_claims must be true")
    if payload["seed"] != DEFAULT_SEED:
        raise ValueError(f"{label}: seed must be {DEFAULT_SEED}")


def run_scenario(scenario: str, *, enrich_from_api: bool = False) -> dict[str, Any]:
    """Run a deterministic Phase 8 scenario and write artifacts."""
    if scenario not in SCENARIO_NAMES:
        raise ValueError(f"Unknown scenario: {scenario}")

    random.seed(DEFAULT_SEED)
    try:
        import numpy as np

        np.random.seed(DEFAULT_SEED)
    except ImportError:
        pass

    run_id = str(uuid4())
    trace_id = f"phase8-{run_id[:8]}"
    generated_at = datetime.now(tz=UTC).isoformat()
    anomaly = scenario == "anomaly_safety_intervention"

    timeline = _build_scenario_timeline(scenario, trace_id=trace_id, run_id=run_id, anomaly=anomaly)
    limitations = _scenario_limitations(scenario)
    components = _components_touched(scenario)
    evidence = build_evidence_index(force_refresh=True)

    mission_status: dict[str, Any] | None = None
    if enrich_from_api:
        try:
            mission_status = build_mission_status(force_refresh=True)
        except Exception:  # noqa: BLE001
            limitations.append("Live mission status enrichment failed — artifact-only result")

    scenario_payload: dict[str, Any] = {
        "run_id": run_id,
        "scenario": scenario,
        "generated_at": generated_at,
        "trace_id": trace_id,
        "phase": PHASE,
        "seed": DEFAULT_SEED,
        "synthetic_data_only": True,
        "no_medical_claims": True,
        "status": "completed",
        "timeline": timeline,
        "components_touched": components,
        "evidence_links": [item["path"] for item in evidence["items"] if item.get("exists")][:12],
        "limitations": limitations,
        "repo_commit": _git_commit(),
    }
    if mission_status:
        scenario_payload["mission_status_snapshot"] = {
            "system_mode": mission_status.get("system_mode"),
            "degraded_components": mission_status.get("degraded_components"),
        }

    validate_artifact_payload(scenario_payload, label="scenario artifact")

    PHASE8_DIR.mkdir(parents=True, exist_ok=True)

    scenario_path = PHASE8_DIR / f"phase8_scenario_{scenario}_{run_id}.json"
    scenario_path.write_text(json.dumps(scenario_payload, indent=2), encoding="utf-8")

    status_payload = {
        "run_id": run_id,
        "scenario": scenario,
        "generated_at": generated_at,
        "phase": PHASE,
        "seed": DEFAULT_SEED,
        "synthetic_data_only": True,
        "no_medical_claims": True,
        "system_mode": "scenario_artifact",
        "components": components,
        "limitations": limitations,
        "repo_commit": _git_commit(),
    }
    validate_artifact_payload(status_payload, label="mission status artifact")
    MISSION_STATUS_ARTIFACT.write_text(json.dumps(status_payload, indent=2), encoding="utf-8")

    timeline_payload = {
        "run_id": run_id,
        "scenario": scenario,
        "generated_at": generated_at,
        "phase": PHASE,
        "seed": DEFAULT_SEED,
        "synthetic_data_only": True,
        "no_medical_claims": True,
        "events": timeline,
        "limitations": limitations,
        "repo_commit": _git_commit(),
    }
    validate_artifact_payload(timeline_payload, label="timeline artifact")
    MISSION_TIMELINE_ARTIFACT.write_text(json.dumps(timeline_payload, indent=2), encoding="utf-8")

    evidence_payload = {
        **evidence,
        "run_id": run_id,
        "scenario": scenario,
        "generated_at": generated_at,
        "seed": DEFAULT_SEED,
        "limitations": limitations,
        "repo_commit": _git_commit(),
    }
    validate_artifact_payload(evidence_payload, label="evidence index artifact")
    MISSION_EVIDENCE_INDEX_ARTIFACT.write_text(
        json.dumps(evidence_payload, indent=2),
        encoding="utf-8",
    )

    summary_lines = [
        "Phase 8 Mission Scenario Summary",
        f"Scenario: {scenario}",
        f"Run ID: {run_id}",
        f"Generated: {generated_at}",
        f"Seed: {DEFAULT_SEED}",
        "",
        "Components touched:",
        *[f"  - {c}" for c in components],
        "",
        "Artifacts:",
        f"  - {scenario_path.relative_to(PHASE8_DIR.parents[1])}",
        f"  - {MISSION_STATUS_ARTIFACT.relative_to(PHASE8_DIR.parents[1])}",
        f"  - {MISSION_TIMELINE_ARTIFACT.relative_to(PHASE8_DIR.parents[1])}",
        f"  - {MISSION_EVIDENCE_INDEX_ARTIFACT.relative_to(PHASE8_DIR.parents[1])}",
        "",
        "Limitations:",
        *[f"  - {lim}" for lim in limitations],
        "",
        "Synthetic data only. No medical claims.",
    ]
    SCENARIO_SUMMARY_ARTIFACT.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return {
        "run_id": run_id,
        "scenario": scenario,
        "status": "completed",
        "timeline": timeline,
        "artifact_paths": {
            "scenario": str(scenario_path),
            "mission_status": str(MISSION_STATUS_ARTIFACT),
            "mission_timeline": str(MISSION_TIMELINE_ARTIFACT),
            "mission_evidence_index": str(MISSION_EVIDENCE_INDEX_ARTIFACT),
            "scenario_summary": str(SCENARIO_SUMMARY_ARTIFACT),
        },
        "limitations": limitations,
        "synthetic_data_only": True,
        "no_medical_claims": True,
        "seed": DEFAULT_SEED,
    }


def list_scenarios() -> dict[str, Any]:
    """Return available Phase 8 scenario definitions."""
    definitions = {
        "normal_operation": {
            "title": "Normal Operation",
            "description": (
                "Nominal synthetic telemetry through inference, safety, agent decision, "
                "twin/status checks, and evidence write."
            ),
        },
        "anomaly_safety_intervention": {
            "title": "Anomaly Safety Intervention",
            "description": (
                "Synthetic elevated signals trigger safety/HITL gate with controlled "
                "operational action proposal."
            ),
        },
        "learning_evidence_review": {
            "title": "Learning Evidence Review",
            "description": (
                "Connect FL/RL evidence to the mission view without retraining."
            ),
        },
    }
    return {
        "phase": PHASE,
        "scenarios": [
            {"name": name, **definitions[name]} for name in SCENARIO_NAMES
        ],
        "synthetic_data_only": True,
        "no_medical_claims": True,
    }
