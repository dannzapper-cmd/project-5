#!/usr/bin/env python3
"""Phase 7A reliability checks — local, no cloud/VM/Kubernetes required."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
RELIABILITY_DIR = ROOT / "artifacts" / "reliability"

ALLOWED_STATUSES = {"ok", "degraded", "unavailable", "inactive", "error"}
REQUIRED_TOP_KEYS = {"status", "service", "timestamp", "components"}


def _fetch_json(url: str, timeout: float = 5.0) -> tuple[int | None, dict | list | None, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body), body
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode()
            return exc.code, json.loads(body), body
        except Exception:
            return exc.code, None, str(exc)
    except Exception as exc:
        return None, None, str(exc)


def validate_status_schema(data: dict, label: str) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"{label}: missing top-level key {key!r}")
    components = data.get("components")
    if not isinstance(components, dict):
        errors.append(f"{label}: components must be an object")
        return errors
    for name, comp in components.items():
        if not isinstance(comp, dict):
            errors.append(f"{label}.{name}: component must be an object")
            continue
        for field in ("status", "required", "message"):
            if field not in comp:
                errors.append(f"{label}.{name}: missing {field!r}")
        status = comp.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{label}.{name}: invalid status {status!r}")
        if "required" in comp and not isinstance(comp["required"], bool):
            errors.append(f"{label}.{name}: required must be boolean")
    return errors


def run_checks(api_base: str, offline: bool, output_dir: Path | None = None) -> dict:
    run_id = str(uuid4())
    timestamp = datetime.now(UTC).isoformat()
    checks: list[dict] = []
    reliability_dir = output_dir or RELIABILITY_DIR

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    live_ok = False
    ready_ok = False
    services_ok = False
    metrics_ok = False
    service_snapshot: dict | None = None

    if offline:
        record("offline_mode", True, "Skipping live API checks (--offline)")
    else:
        status, live, _ = _fetch_json(f"{api_base}/health/live")
        live_ok = status == 200 and isinstance(live, dict) and live.get("status") == "ok"
        record(
            "health_live",
            live_ok,
            f"HTTP {status}, body status={live.get('status') if isinstance(live, dict) else live}",
        )

        status, ready, _ = _fetch_json(f"{api_base}/health/ready")
        ready_errors: list[str] = []
        if isinstance(ready, dict):
            ready_errors = validate_status_schema(ready, "ready")
        ready_ok = status in (200, 503) and isinstance(ready, dict) and not ready_errors
        ready_agg = ready.get("status") if isinstance(ready, dict) else ready
        ready_detail = "; ".join(ready_errors) if ready_errors else "schema ok"
        record(
            "health_ready",
            ready_ok,
            f"HTTP {status}, aggregate={ready_agg}; {ready_detail}",
        )

        status, services, _ = _fetch_json(f"{api_base}/status/services")
        service_errors: list[str] = []
        if isinstance(services, dict):
            service_errors = validate_status_schema(services, "services")
            service_snapshot = services
        services_ok = status == 200 and isinstance(services, dict) and not service_errors
        services_agg = (
            services.get("status") if isinstance(services, dict) else services
        )
        services_detail = (
            "; ".join(service_errors) if service_errors else "schema ok"
        )
        record(
            "status_services",
            services_ok,
            f"HTTP {status}, aggregate={services_agg}; {services_detail}",
        )

        try:
            with urllib.request.urlopen(f"{api_base}/metrics", timeout=5) as resp:
                metrics_body = resp.read().decode()
                metrics_ok = resp.status == 200 and len(metrics_body.strip()) > 0
                for needle in (
                    "axon_api_requests_total",
                    "axon_api_errors_total",
                    "axon_degraded_components_total",
                ):
                    if needle not in metrics_body:
                        metrics_ok = False
                        record("metrics_content", False, f"missing {needle}")
                record("metrics", metrics_ok, f"HTTP {resp.status}, bytes={len(metrics_body)}")
        except Exception as exc:
            record("metrics", False, str(exc))

    # Failure replay: validate graceful handling when optional evidence missing
    fl_report = ROOT / "artifacts" / "learning" / "federated" / "federated_report.json"
    rl_report = ROOT / "artifacts" / "learning" / "rl" / "rl_report.json"
    fl_missing = not fl_report.is_file()
    rl_missing = not rl_report.is_file()
    failure_notes = []
    if service_snapshot:
        fl_status = service_snapshot.get("components", {}).get("fl_module", {}).get("status")
        rl_status = service_snapshot.get("components", {}).get("rl_module", {}).get("status")
        if fl_missing and fl_status not in ("unavailable", "inactive", "degraded"):
            failure_notes.append(f"fl_module status={fl_status} but report missing")
        if rl_missing and rl_status not in ("unavailable", "inactive", "degraded"):
            failure_notes.append(f"rl_module status={rl_status} but report missing")
        record(
            "failure_replay_optional_evidence",
            not failure_notes,
            "; ".join(failure_notes) if failure_notes else "optional evidence degrades gracefully",
        )
    else:
        record(
            "failure_replay_optional_evidence",
            True,
            "skipped (no service snapshot — offline or API down)",
        )

    passed = all(c["passed"] for c in checks)
    summary = "pass" if passed else ("partial" if any(c["passed"] for c in checks) else "fail")

    reliability_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": run_id,
        "timestamp": timestamp,
        "phase": "phase7",
        "api_base": api_base,
        "offline": offline,
        "summary": summary,
        "checks": checks,
    }
    (reliability_dir / "phase7a_reliability_report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    if service_snapshot:
        (reliability_dir / "service_status_snapshot.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "phase": "phase7",
                    "snapshot": service_snapshot,
                },
                indent=2,
            )
            + "\n"
        )
    failure_replay = {
        "run_id": run_id,
        "timestamp": timestamp,
        "phase": "phase7",
        "summary": summary,
        "scenarios": [
            {
                "scenario": "fl_artifacts_missing",
                "artifact_present": fl_report.is_file(),
                "expected_statuses": ["unavailable", "inactive", "degraded"],
                "observed": service_snapshot.get("components", {}).get("fl_module")
                if service_snapshot
                else None,
            },
            {
                "scenario": "rl_artifacts_missing",
                "artifact_present": rl_report.is_file(),
                "expected_statuses": ["unavailable", "inactive", "degraded"],
                "observed": service_snapshot.get("components", {}).get("rl_module")
                if service_snapshot
                else None,
            },
            {
                "scenario": "mlflow_unavailable",
                "expected_statuses": ["unavailable", "inactive", "degraded"],
                "observed": service_snapshot.get("components", {}).get("mlflow")
                if service_snapshot
                else None,
            },
        ],
        "checks": [
            c
            for c in checks
            if "failure_replay" in c["check"] or c["check"].startswith("health")
        ],
    }
    (reliability_dir / "failure_replay_report.json").write_text(
        json.dumps(failure_replay, indent=2) + "\n"
    )

    print(json.dumps(report, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 7A AXON reliability checks")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip live API checks; still write artifact scaffolding",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated reports (defaults to committed evidence path)",
    )
    args = parser.parse_args()
    report = run_checks(args.api_base, args.offline, args.output_dir)
    return 0 if report["summary"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
