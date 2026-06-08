"""In-memory Phase 7 metrics and Prometheus text rendering."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from apps.api.app.reliability.service_status import (
    aggregate_status,
    compute_components,
    count_degraded_components,
    count_evidence_files,
)
from apps.api.app.telemetry.state import telemetry_state


@dataclass
class ApiMetrics:
    requests_total: int = 0
    errors_total: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc_request(self) -> None:
        with self._lock:
            self.requests_total += 1

    def inc_error(self) -> None:
        with self._lock:
            self.errors_total += 1


api_metrics = ApiMetrics()


def render_prometheus_text() -> str:
    components = compute_components()
    degraded = count_degraded_components(components)
    evidence_present, evidence_missing = count_evidence_files()
    agg = aggregate_status(components)
    overall = 0 if agg == "ok" else 1

    lines = [
        "# HELP axon_api_requests_total Total API HTTP requests observed by Phase 7 middleware.",
        "# TYPE axon_api_requests_total counter",
        f"axon_api_requests_total {api_metrics.requests_total}",
        "# HELP axon_api_errors_total Total API HTTP 5xx responses observed by Phase 7 middleware.",
        "# TYPE axon_api_errors_total counter",
        f"axon_api_errors_total {api_metrics.errors_total}",
        "# HELP axon_service_status Overall service status gauge (0=ok-ish, 1=not ok).",
        "# TYPE axon_service_status gauge",
        f"axon_service_status {overall}",
        "# HELP axon_degraded_components_total Components in degraded/unavailable/error state.",
        "# TYPE axon_degraded_components_total gauge",
        f"axon_degraded_components_total {degraded}",
        "# HELP axon_evidence_files_present_total Known evidence files present on disk.",
        "# TYPE axon_evidence_files_present_total gauge",
        f"axon_evidence_files_present_total {evidence_present}",
        "# HELP axon_evidence_files_missing_total Known evidence files missing on disk.",
        "# TYPE axon_evidence_files_missing_total gauge",
        f"axon_evidence_files_missing_total {evidence_missing}",
        "# HELP axon_last_telemetry_timestamp Unix epoch of last telemetry event if known.",
        "# TYPE axon_last_telemetry_timestamp gauge",
        f"axon_last_telemetry_timestamp {0}",
    ]
    if telemetry_state.last_model_score_at:
        lines.append(
            "# HELP axon_last_model_score_timestamp Last model score timestamp string exported as info."
        )
        lines.append("# TYPE axon_last_model_score_timestamp gauge")
        lines.append("axon_last_model_score_timestamp 0")
    return "\n".join(lines) + "\n"
