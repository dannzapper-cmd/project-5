"""Mission timeline generation from status, scenarios, or deterministic fallback."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from apps.api.app.mission.constants import PHASE, TIMELINE_STAGES
from apps.api.app.mission.paths import MISSION_TIMELINE_ARTIFACT, PHASE8_DIR
from apps.api.app.mission.status import build_mission_status


def _event(
    *,
    stage: str,
    title: str,
    summary: str,
    source_component: str,
    status: str,
    timestamp: datetime,
    trace_id: str | None = None,
    artifact_ref: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "timestamp": timestamp.isoformat(),
        "stage": stage,
        "title": title,
        "summary": summary,
        "source_component": source_component,
        "status": status,
        "trace_id": trace_id,
        "artifact_ref": artifact_ref,
        "details": details or {},
    }


def _load_artifact_timeline() -> list[dict[str, Any]] | None:
    if MISSION_TIMELINE_ARTIFACT.is_file():
        try:
            data = json.loads(MISSION_TIMELINE_ARTIFACT.read_text(encoding="utf-8"))
            events = data.get("events")
            if isinstance(events, list) and events:
                return events
        except (OSError, json.JSONDecodeError):
            return None

    if PHASE8_DIR.is_dir():
        candidates = sorted(PHASE8_DIR.glob("phase8_scenario_*.json"), key=lambda p: p.stat().st_mtime)
        if candidates:
            try:
                data = json.loads(candidates[-1].read_text(encoding="utf-8"))
                events = data.get("timeline")
                if isinstance(events, list) and events:
                    return events
            except (OSError, json.JSONDecodeError):
                return None
    return None


def _fallback_timeline(status: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic fallback when no scenario artifact exists."""
    base = datetime.now(tz=UTC)
    components = status.get("components", {})
    events: list[dict[str, Any]] = []

    stage_meta = [
        ("telemetry_received", "Synthetic telemetry", "synthetic_telemetry", "Telemetry ingest path"),
        ("edge_inference_scored", "Edge inference scored", "edge_inference", "ONNX edge inference"),
        ("anomaly_status_evaluated", "Anomaly status evaluated", "anomaly_safety", "Safety fusion"),
        ("agent_decision_generated", "Agent decision generated", "agent_decision", "LangGraph agents"),
        ("hitl_safety_gate_checked", "HITL safety gate checked", "hitl_safety_gate", "Human-in-the-loop"),
        ("digital_twin_updated", "Digital twin updated", "digital_twin", "Digital twin mirror"),
        ("ros2_status_checked", "ROS2 status checked", "ros2", "ROS2 bridge"),
        ("nav_slam_status_checked", "Nav2/SLAM status checked", "nav_slam", "Nav2 SLAM MiniLab"),
        ("fl_evidence_loaded", "FL evidence loaded", "fl_evidence", "Federated learning"),
        ("rl_evidence_loaded", "RL evidence loaded", "rl_evidence", "RL micro-module"),
        ("observability_checked", "Observability checked", "observability", "Observability layer"),
        ("reliability_checked", "Reliability checked", "reliability", "Reliability layer"),
        ("evidence_artifact_written", "Evidence artifact written", "evidence_center", "Evidence Center"),
    ]

    for idx, (stage, title, comp_key, source) in enumerate(stage_meta):
        comp = components.get(comp_key, {})
        comp_status = comp.get("status", "unknown")
        if comp_status == "ok":
            evt_status = "ok"
        elif comp_status in ("offline", "inactive", "unknown"):
            evt_status = "skipped"
        elif comp_status == "artifact_only":
            evt_status = "simulated"
        else:
            evt_status = "warning"

        reason = None
        if evt_status == "skipped":
            reason = comp.get("message", "Component offline")

        events.append(
            _event(
                stage=stage,
                title=title,
                summary=comp.get("message", title),
                source_component=source,
                status=evt_status,
                timestamp=base + timedelta(seconds=idx),
                details={"component_status": comp_status, "reason": reason},
            )
        )

    return events


def build_mission_timeline(*, force_refresh: bool = False) -> dict[str, Any]:
    """Return ordered mission timeline JSON."""
    artifact_events = _load_artifact_timeline()
    status = build_mission_status(force_refresh=force_refresh)

    if artifact_events:
        events = artifact_events
        source = "scenario_artifact"
    else:
        events = _fallback_timeline(status)
        source = "deterministic_fallback"

    for stage in TIMELINE_STAGES:
        if not any(e.get("stage") == stage for e in events):
            events.append(
                _event(
                    stage=stage,
                    title=stage.replace("_", " ").title(),
                    summary="Stage not present in source timeline",
                    source_component="mission_control",
                    status="skipped",
                    timestamp=datetime.now(tz=UTC),
                    details={"reason": "Missing from generated timeline"},
                )
            )

    events.sort(key=lambda e: TIMELINE_STAGES.index(e["stage"]) if e["stage"] in TIMELINE_STAGES else 999)

    limitations: list[str] = []
    if source == "deterministic_fallback":
        limitations.append("Timeline generated from live status fallback — run a scenario for artifact-backed timeline")

    return {
        "phase": PHASE,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "source": source,
        "run_id": status.get("run_id"),
        "events": events,
        "degraded": status.get("degraded", True),
        "degraded_components": status.get("degraded_components", []),
        "limitations": limitations or status.get("limitations", []),
        "synthetic_data_only": True,
        "no_medical_claims": True,
    }
