"""Unified mission status snapshot (artifact-backed, cached, non-blocking)."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.api.app.agents.service import (
    get_current_decision,
    get_safety_status,
)
from apps.api.app.mission.constants import PHASE, STATUS_TTL_S
from apps.api.app.mission.evidence_index import build_evidence_index
from apps.api.app.mission.paths import (
    FL_ARTIFACTS,
    MISSION_STATUS_ARTIFACT,
    OBSERVABILITY_ARTIFACTS,
    PHASE8_DIR,
    RELIABILITY_ARTIFACTS,
    RL_ARTIFACTS,
)
from apps.api.app.nav_slam.service import get_service_status as get_nav_slam_status
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.twin.service import get_latest_twin_state, get_twin_service_status

_status_cache: dict[str, Any] | None = None
_status_cache_ts: float = 0.0


def _artifact_component(
    name: str,
    path: Path,
    *,
    ok_message: str,
    offline_message: str,
) -> dict[str, Any]:
    if path.is_file():
        mtime = path.stat().st_mtime
        age_s = time.time() - mtime
        stale = age_s > STATUS_TTL_S
        return {
            "status": "artifact_only" if stale else "ok",
            "message": ok_message,
            "artifact_path": str(path),
            "stale": stale,
        }
    return {
        "status": "offline",
        "message": offline_message,
    }


def _runtime_component(name: str, ok: bool, *, ok_msg: str, offline_msg: str) -> dict[str, Any]:
    if ok:
        return {"status": "ok", "message": ok_msg}
    return {"status": "offline", "message": offline_msg}


def _load_latest_scenario_meta() -> dict[str, Any]:
    if not PHASE8_DIR.is_dir():
        return {}
    candidates = sorted(PHASE8_DIR.glob("phase8_scenario_*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        return {}
    try:
        data = json.loads(candidates[-1].read_text(encoding="utf-8"))
        return {
            "run_id": data.get("run_id"),
            "scenario": data.get("scenario"),
            "generated_at": data.get("generated_at"),
        }
    except (OSError, json.JSONDecodeError):
        return {}


def _service_readiness_summary() -> dict[str, Any]:
    try:
        from apps.api.app.reliability.service_status import build_service_status

        services = build_service_status(trace_id=None)
        return {
            "status": services.get("status", "unknown"),
            "components": services.get("components", {}),
        }
    except Exception as exc:  # noqa: BLE001 — degrade gracefully
        return {
            "status": "unknown",
            "message": f"Service status unavailable: {exc}",
            "components": {},
        }


def build_mission_status(*, force_refresh: bool = False) -> dict[str, Any]:
    """Build unified mission status; never raises for optional offline components."""
    global _status_cache, _status_cache_ts

    now = time.time()
    if (
        not force_refresh
        and _status_cache is not None
        and (now - _status_cache_ts) < STATUS_TTL_S
    ):
        return dict(_status_cache)

    scenario_meta = _load_latest_scenario_meta()
    twin_status = get_twin_service_status()
    twin_state = get_latest_twin_state()
    nav_slam = get_nav_slam_status()
    safety = get_safety_status()
    decision = get_current_decision()

    telemetry_ok = telemetry_state.mqtt_connected and telemetry_state.redis_connected
    inference_ok = telemetry_state.model_score_stream_connected or telemetry_state.model_scores_received > 0
    twin_ok = bool(twin_status.get("running"))
    agents_ok = decision is not None or bool(safety)
    hitl_pending = decision is not None and decision.get("requires_human_confirmation")

    ros2_status = "offline"
    if twin_state is not None:
        ros2_status = twin_state.ros2_bridge.status

    components = {
        "synthetic_telemetry": _runtime_component(
            "synthetic_telemetry",
            telemetry_ok,
            ok_msg="Telemetry pipeline connected",
            offline_msg="Telemetry pipeline offline or not connected",
        ),
        "edge_inference": _runtime_component(
            "edge_inference",
            inference_ok,
            ok_msg="Edge inference active or scores observed",
            offline_msg="Edge inference inactive",
        ),
        "anomaly_safety": {
            "status": "ok" if safety else "unknown",
            "message": "Safety evaluator in-process",
            "high_risk": safety.get("high_risk"),
            "stale_telemetry": safety.get("stale_telemetry"),
        },
        "agent_decision": {
            "status": "ok" if decision else "offline",
            "message": "Current agent decision available" if decision else "No agent decision yet",
            "action": (decision or {}).get("proposed_action"),
        },
        "hitl_safety_gate": {
            "status": "ok" if hitl_pending else ("offline" if not decision else "ok"),
            "message": "HITL confirmation pending"
            if hitl_pending
            else "No pending HITL gate",
            "requires_human_confirmation": hitl_pending,
        },
        "digital_twin": _runtime_component(
            "digital_twin",
            twin_ok,
            ok_msg=f"Twin broadcast at {twin_status.get('broadcast_hz')} Hz",
            offline_msg="Digital twin broadcast not running",
        ),
        "ros2": {
            "status": "ok" if ros2_status not in ("offline", "unknown") else "offline",
            "message": f"ROS2 bridge status: {ros2_status}",
            "bridge_status": ros2_status,
        },
        "nav_slam": {
            "status": nav_slam.get("bridge_status", "offline"),
            "message": (
                f"Nav={nav_slam.get('nav_status')}, SLAM={nav_slam.get('slam_status')}"
            ),
            "nav_status": nav_slam.get("nav_status"),
            "slam_status": nav_slam.get("slam_status"),
        },
        "fl_evidence": _artifact_component(
            "fl_evidence",
            FL_ARTIFACTS["federated_report"],
            ok_message="Federated learning report present",
            offline_message="FL report missing",
        ),
        "rl_evidence": _artifact_component(
            "rl_evidence",
            RL_ARTIFACTS["rl_report"],
            ok_message="RL report present",
            offline_message="RL report missing",
        ),
        "observability": _artifact_component(
            "observability",
            OBSERVABILITY_ARTIFACTS["phase7b_report"],
            ok_message="Observability report present",
            offline_message="Observability report missing",
        ),
        "reliability": _artifact_component(
            "reliability",
            RELIABILITY_ARTIFACTS["phase7a_report"],
            ok_message="Reliability report present",
            offline_message="Reliability report missing",
        ),
    }

    evidence = build_evidence_index(force_refresh=True)
    evidence_available = evidence["summary"]["available"] > 0
    components["evidence_center"] = {
        "status": "ok" if evidence_available else "offline",
        "message": f"{evidence['summary']['available']} evidence items available",
        "total_items": evidence["summary"]["total"],
    }

    service_readiness = _service_readiness_summary()
    components["service_readiness"] = {
        "status": service_readiness.get("status", "unknown"),
        "message": "Aggregated from /status/services",
    }

    degraded_components: list[str] = []
    limitations: list[str] = []

    for name, comp in components.items():
        status = comp.get("status", "unknown")
        if status not in ("ok",):
            degraded_components.append(name)
        if status == "offline":
            limitations.append(f"{name} is offline or unavailable without live services")
        elif status == "artifact_only":
            limitations.append(f"{name} using artifact-only fallback (runtime not verified)")

    if not scenario_meta:
        limitations.append("No Phase 8 scenario has been run yet; timeline uses deterministic fallback")

    if nav_slam.get("bridge_status") in ("offline", "inactive", None):
        limitations.append("Nav2/SLAM MiniLab not running — status from in-process stub or artifacts")

    if ros2_status == "offline":
        limitations.append("ROS2 bridge offline — no live robotics runtime required for Phase 8")

    system_mode = "integrated_mission_control"
    if telemetry_ok and twin_ok:
        system_mode = "live_core"
    elif scenario_meta:
        system_mode = "scenario_artifact"

    payload: dict[str, Any] = {
        "mission_id": scenario_meta.get("run_id"),
        "run_id": scenario_meta.get("run_id"),
        "phase": PHASE,
        "system_mode": system_mode,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "scenario": scenario_meta.get("scenario"),
        "components": components,
        "service_readiness": service_readiness,
        "evidence_center_summary": evidence["summary"],
        "degraded": bool(degraded_components),
        "degraded_components": degraded_components,
        "limitations": limitations or ["Core API reachable; optional profiles may be offline"],
        "links": {
            "health_live": "/health/live",
            "health_ready": "/health/ready",
            "status_services": "/status/services",
            "metrics": "/metrics",
            "mission_timeline": "/mission/timeline",
            "mission_evidence": "/mission/evidence",
            "federated_status": "/api/learning/federated/status",
            "rl_status": "/api/learning/rl/status",
            "twin_status": "/api/v1/twin/status",
            "nav_slam_status": "/api/v1/nav-slam/status",
        },
        "synthetic_data_only": True,
        "no_medical_claims": True,
    }

    if MISSION_STATUS_ARTIFACT.is_file():
        try:
            cached = json.loads(MISSION_STATUS_ARTIFACT.read_text(encoding="utf-8"))
            if cached.get("run_id"):
                payload["last_scenario_artifact"] = str(MISSION_STATUS_ARTIFACT.relative_to(MISSION_STATUS_ARTIFACT.parents[2]))
        except (OSError, json.JSONDecodeError):
            pass

    _status_cache = payload
    _status_cache_ts = now
    return dict(payload)
