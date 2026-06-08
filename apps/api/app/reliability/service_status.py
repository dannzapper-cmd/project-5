"""Aggregate AXON component status for /health/ready and /status/services."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from apps.api.app.core.config import settings
from apps.api.app.nav_slam.service import get_service_status as get_nav_slam_status
from apps.api.app.observability import events
from apps.api.app.observability.structured_log import log_event
from apps.api.app.reliability.dependency_checks import (
    ALLOWED_STATUSES,
    ComponentCheck,
    artifact_exists,
    check_mlflow,
    check_mqtt,
    check_redis,
)
from apps.api.app.reliability.paths import FL_REPORT, MLOPS_REGISTRY, RL_REPORT
from apps.api.app.telemetry.state import telemetry_state
from apps.api.app.twin.service import get_latest_twin_state, get_twin_service_status

StatusValue = str


def _component_dict(check: ComponentCheck) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status": check.status,
        "required": check.required,
        "message": check.message,
    }
    if check.error_type:
        out["error_type"] = check.error_type
    return out


def _safe_check(name: str, fn) -> dict[str, Any]:
    try:
        return _component_dict(fn())
    except Exception as exc:  # noqa: BLE001 — per-component isolation
        return {
            "status": "error",
            "required": False,
            "message": f"{name} check raised: {exc}",
            "error_type": type(exc).__name__,
        }


def _telemetry_pipeline_status() -> ComponentCheck:
    if telemetry_state.redis_connected and telemetry_state.mqtt_connected:
        return ComponentCheck(
            status="ok",
            required=False,
            message="Telemetry pipeline connected (MQTT ingest + Redis streams)",
        )
    parts = []
    if not telemetry_state.mqtt_connected:
        parts.append("MQTT not connected")
    if not telemetry_state.redis_connected:
        parts.append("Redis not connected")
    return ComponentCheck(
        status="degraded",
        required=False,
        message="; ".join(parts) or "Telemetry pipeline degraded",
    )


def _edge_inference_status() -> ComponentCheck:
    if telemetry_state.model_score_stream_connected:
        return ComponentCheck(
            status="ok",
            required=False,
            message="Edge inference model-score stream connected",
        )
    if telemetry_state.model_scores_received > 0:
        return ComponentCheck(
            status="degraded",
            required=False,
            message="Edge inference scores seen but stream watcher not connected",
        )
    return ComponentCheck(
        status="inactive",
        required=False,
        message="Edge inference inactive or no model scores yet",
    )


def _digital_twin_status() -> ComponentCheck:
    twin_status = get_twin_service_status()
    if twin_status.get("running"):
        return ComponentCheck(
            status="ok",
            required=False,
            message=f"Digital twin broadcast running at {twin_status.get('broadcast_hz')} Hz",
        )
    return ComponentCheck(
        status="degraded",
        required=False,
        message="Digital twin broadcast loop not running",
    )


def _agents_hitl_status() -> ComponentCheck:
    return ComponentCheck(
        status="ok",
        required=False,
        message="Agents/HITL loop available via API (mock or real LLM mode)",
    )


def _ros2_status() -> ComponentCheck:
    twin = get_latest_twin_state()
    bridge = twin.ros2_bridge.status if twin else "offline"
    if bridge in ("online", "connected", "active"):
        return ComponentCheck(
            status="ok",
            required=False,
            message=f"ROS2 bridge status: {bridge}",
        )
    if bridge == "offline":
        return ComponentCheck(
            status="inactive",
            required=False,
            message="ROS2 profile not active or bridge offline",
        )
    return ComponentCheck(
        status="unavailable",
        required=False,
        message=f"ROS2 bridge status: {bridge}",
    )


def _ros2_nav_slam_status() -> ComponentCheck:
    nav = get_nav_slam_status()
    bridge = nav.get("bridge_status", "offline")
    if bridge == "offline":
        return ComponentCheck(
            status="inactive",
            required=False,
            message="Nav2/SLAM MiniLab profile not active or bridge offline",
        )
    if bridge in ("online", "active", "degraded"):
        return ComponentCheck(
            status="ok" if bridge != "degraded" else "degraded",
            required=False,
            message=f"Nav2/SLAM bridge: {bridge}; nav={nav.get('nav_status')}, slam={nav.get('slam_status')}",
        )
    return ComponentCheck(
        status="unavailable",
        required=False,
        message=f"Nav2/SLAM bridge status: {bridge}",
    )


def _dashboard_status() -> ComponentCheck:
    return ComponentCheck(
        status="inactive",
        required=False,
        message="Dashboard is a separate static server; not probed from API",
    )


def _mlops_evidence_status() -> ComponentCheck:
    return artifact_exists(MLOPS_REGISTRY, "MLOps registry")


def compute_components() -> dict[str, dict[str, Any]]:
    """Run all component checks; each wrapped for isolation."""
    checks: dict[str, Any] = {
        "api": _component_dict(
            ComponentCheck(status="ok", required=True, message="API process serving requests")
        ),
        "dashboard": _safe_check("dashboard", _dashboard_status),
        "redis": _safe_check("redis", check_redis),
        "mqtt": _safe_check("mqtt", check_mqtt),
        "telemetry_pipeline": _safe_check("telemetry_pipeline", _telemetry_pipeline_status),
        "edge_inference": _safe_check("edge_inference", _edge_inference_status),
        "digital_twin": _safe_check("digital_twin", _digital_twin_status),
        "agents_hitl": _safe_check("agents_hitl", _agents_hitl_status),
        "fl_module": _safe_check(
            "fl_module",
            lambda: artifact_exists(FL_REPORT, "Federated learning"),
        ),
        "rl_module": _safe_check(
            "rl_module",
            lambda: artifact_exists(RL_REPORT, "RL micro-module"),
        ),
        "mlflow": _safe_check("mlflow", check_mlflow),
        "mlops_evidence": _safe_check("mlops_evidence", _mlops_evidence_status),
        "ros2": _safe_check("ros2", _ros2_status),
        "ros2_nav_slam": _safe_check("ros2_nav_slam", _ros2_nav_slam_status),
    }
    return checks


def aggregate_status(components: dict[str, dict[str, Any]]) -> StatusValue:
    required_errors = [
        name
        for name, c in components.items()
        if c.get("required") and c.get("status") in ("error", "unavailable")
    ]
    if required_errors:
        return "error"

    optional_bad = [
        c.get("status")
        for c in components.values()
        if not c.get("required") and c.get("status") in ("error", "unavailable", "degraded")
    ]
    required_degraded = any(
        c.get("required") and c.get("status") == "degraded" for c in components.values()
    )
    if required_degraded or optional_bad:
        return "degraded"
    return "ok"


def build_service_status(*, trace_id: str | None = None) -> dict[str, Any]:
    components = compute_components()
    status = aggregate_status(components)
    payload = {
        "status": status,
        "service": settings.service_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "components": components,
    }
    log_event(
        level="debug" if status == "ok" else "info",
        service=settings.service_name,
        event=events.SERVICE_STATUS_COMPUTED,
        message=f"Service status computed: {status}",
        status=status,
        trace_id=trace_id,
        component="service_status",
    )
    if status == "degraded":
        degraded = [
            name
            for name, c in components.items()
            if c.get("status") in ("degraded", "unavailable", "error") and not c.get("required")
        ]
        if degraded:
            log_event(
                level="info",
                service=settings.service_name,
                event=events.DEGRADED_DEPENDENCY_DETECTED,
                message=f"Optional dependencies degraded: {', '.join(degraded)}",
                status="degraded",
                trace_id=trace_id,
                component="service_status",
            )
    return payload


def build_readiness(*, trace_id: str | None = None) -> dict[str, Any]:
    components = compute_components()
    status = aggregate_status(components)
    payload = {
        "status": status,
        "service": settings.service_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "components": components,
    }
    log_event(
        level="debug" if status == "ok" else "info",
        service=settings.service_name,
        event=events.READINESS_CHECK_COMPLETED,
        message=f"Readiness check completed: {status}",
        status=status,
        trace_id=trace_id,
        component="readiness",
    )
    return payload


def count_degraded_components(components: dict[str, dict[str, Any]]) -> int:
    return sum(
        1
        for c in components.values()
        if c.get("status") in ("degraded", "unavailable", "error")
    )


def count_evidence_files() -> tuple[int, int]:
    from apps.api.app.reliability.paths import (
        FL_REPORT,
        FL_STATUS,
        MLOPS_REGISTRY,
        OBSERVABILITY_DIR,
        RELIABILITY_DIR,
        RL_REPORT,
        RL_STATUS,
    )

    candidates = [
        FL_REPORT,
        FL_STATUS,
        RL_REPORT,
        RL_STATUS,
        MLOPS_REGISTRY,
        RELIABILITY_DIR / "phase7a_reliability_report.json",
        OBSERVABILITY_DIR / "phase7b_observability_report.json",
    ]
    present = sum(1 for p in candidates if p.is_file())
    missing = len(candidates) - present
    return present, missing
