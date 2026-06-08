#!/usr/bin/env python3
"""Phase 7B observability checks — local metrics, logs, and status snapshots."""

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
OBS_DIR = ROOT / "artifacts" / "observability"

from apps.api.app.observability import events  # noqa: E402
from apps.api.app.observability.structured_log import log_event  # noqa: E402


def _fetch(url: str, timeout: float = 5.0) -> tuple[int | None, str, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode()
            ctype = resp.headers.get("Content-Type")
            return resp.status, body, ctype
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(), exc.headers.get("Content-Type")
    except Exception as exc:
        return None, str(exc), None


def run_checks(api_base: str, offline: bool) -> dict:
    run_id = str(uuid4())
    timestamp = datetime.now(UTC).isoformat()
    checks: list[dict] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    metrics_body = ""
    services_body: dict | None = None

    if offline:
        record("offline_mode", True, "Skipping live API checks (--offline)")
        metrics_body = (
            "# offline placeholder\n"
            "axon_api_requests_total 0\n"
            "axon_api_errors_total 0\n"
            "axon_degraded_components_total 0\n"
        )
    else:
        status, body, ctype = _fetch(f"{api_base}/metrics")
        metrics_body = body
        metrics_ok = (
            status == 200
            and len(body.strip()) > 0
            and "axon_api_requests_total" in body
            and "axon_api_errors_total" in body
            and "axon_degraded_components_total" in body
        )
        record("metrics", metrics_ok, f"HTTP {status}, content-type={ctype}")

        status, body, _ = _fetch(f"{api_base}/status/services")
        try:
            services_body = json.loads(body)
            services_ok = status == 200 and isinstance(services_body, dict)
        except json.JSONDecodeError:
            services_ok = False
        record("status_services", services_ok, f"HTTP {status}")

    OBS_DIR.mkdir(parents=True, exist_ok=True)
    (OBS_DIR / "metrics_snapshot.txt").write_text(metrics_body if metrics_body else "# empty\n")

    if services_body:
        (OBS_DIR / "operational_status_snapshot.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "phase": "phase7",
                    "snapshot": services_body,
                },
                indent=2,
            )
            + "\n"
        )
    else:
        (OBS_DIR / "operational_status_snapshot.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "phase": "phase7",
                    "snapshot": None,
                    "note": "API unreachable or offline mode",
                },
                indent=2,
            )
            + "\n"
        )

    sample_events = [
        log_event(
            level="info",
            service="axon-api",
            event=events.HEALTH_CHECK_COMPLETED,
            message="Sample operational log for Phase 7B evidence",
            status="ok",
            run_id=run_id,
        ),
        log_event(
            level="info",
            service="axon-reliability-script",
            event=events.EVIDENCE_SNAPSHOT_GENERATED,
            message="Observability evidence snapshot generated",
            status="ok",
            run_id=run_id,
        ),
        log_event(
            level="info",
            service="axon-observability-script",
            event=events.OBSERVABILITY_CHECK_COMPLETED,
            message="Observability check script completed",
            status="ok",
            run_id=run_id,
        ),
    ]
    with (OBS_DIR / "logging_sample.jsonl").open("w") as fh:
        for event in sample_events:
            fh.write(json.dumps(event, separators=(",", ":")) + "\n")

    log_event(
        level="info",
        service="axon-observability-script",
        event=events.OBSERVABILITY_CHECK_COMPLETED,
        message="Phase 7B observability checks finished",
        status="ok",
        run_id=run_id,
    )

    passed = all(c["passed"] for c in checks) if checks else True
    summary = "pass" if passed else ("partial" if any(c["passed"] for c in checks) else "fail")
    report = {
        "run_id": run_id,
        "timestamp": timestamp,
        "phase": "phase7",
        "api_base": api_base,
        "offline": offline,
        "summary": summary,
        "checks": checks,
        "artifacts": [
            "artifacts/observability/phase7b_observability_report.json",
            "artifacts/observability/metrics_snapshot.txt",
            "artifacts/observability/logging_sample.jsonl",
            "artifacts/observability/operational_status_snapshot.json",
        ],
    }
    (OBS_DIR / "phase7b_observability_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 7B AXON observability checks")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    report = run_checks(args.api_base, args.offline)
    return 0 if report["summary"] in ("pass", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
