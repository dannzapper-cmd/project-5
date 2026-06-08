# Phase 7 — Observability Layer

Phase 7 adds **structured operational logs**, a **`/metrics` endpoint**, local
evidence artifacts, and a dashboard operational panel — without mandatory
Prometheus/Grafana or heavy OpenTelemetry.

**Safety:** Simulated system only. No real patient data. No clinical use claims.

## Structured JSON logs

Operational events are emitted via `apps/api/app/observability/structured_log.py`.

Required keys on every line:

- `timestamp` (ISO8601 UTC)
- `level`
- `service`
- `event` (stable snake_case name)
- `message`

Optional keys: `trace_id`, `run_id`, `event_id`, `component`, `error_type`, `status`.

### Stable event names

| Event | When |
|-------|------|
| `health_check_completed` | Liveness probe |
| `readiness_check_completed` | Readiness probe |
| `service_status_computed` | `/status/services` computed |
| `degraded_dependency_detected` | Optional dependency degraded |
| `evidence_snapshot_generated` | Evidence file written |
| `metrics_snapshot_generated` | `/metrics` rendered |
| `reliability_check_completed` | Reliability script finished |
| `observability_check_completed` | Observability script finished |
| `dashboard_status_loaded` | Dashboard operational panel (future hook) |

Health probe hits are logged at **DEBUG** to avoid noise.

## Correlation IDs

| ID | Scope |
|----|-------|
| `trace_id` | Per HTTP request (`X-Trace-Id` header accepted; UUID generated if absent) |
| `run_id` | Per reliability/observability script execution |
| `event_id` | Reserved for telemetry events (future) |

## Metrics endpoint

**Route:** `GET /metrics`  
**Format:** Prometheus text exposition (hand-written, no `prometheus-client` dependency)

| Metric | Type | Meaning |
|--------|------|---------|
| `axon_api_requests_total` | counter | HTTP requests seen by Phase 7 middleware |
| `axon_api_errors_total` | counter | HTTP 5xx responses |
| `axon_service_status` | gauge | 0 when any component ok, else 1 |
| `axon_degraded_components_total` | gauge | Count of degraded/unavailable/error components |
| `axon_evidence_files_present_total` | gauge | Known evidence files present on disk |
| `axon_evidence_files_missing_total` | gauge | Known evidence files missing |
| `axon_last_telemetry_timestamp` | gauge | Placeholder 0 until wired to live telemetry clock |

Counters start at **0**. No fake traffic or training success is invented.

## Running observability checks

```bash
python scripts/observability/check_phase7_observability.py --api-base http://localhost:8000
python scripts/observability/check_phase7_observability.py --offline
```

## Evidence artifacts

| File | Description |
|------|-------------|
| `artifacts/observability/phase7b_observability_report.json` | Check summary |
| `artifacts/observability/metrics_snapshot.txt` | Last `/metrics` body or offline placeholder |
| `artifacts/observability/logging_sample.jsonl` | Sample structured log lines |
| `artifacts/observability/operational_status_snapshot.json` | Last `/status/services` snapshot |

## Dashboard

The **Operational Status** panel (Phase 7) shows overall/readiness/liveness status,
core vs optional components, evidence availability, and a simulation disclaimer.
It degrades gracefully when the API is unreachable (no uncaught JS exceptions).

## Prometheus / Grafana decision

**Not expanded in Phase 7.** The existing optional `obs` Docker profile keeps a
placeholder Prometheus self-scrape and Grafana placeholder container. The API
`/metrics` endpoint is sufficient for local review and future scrape wiring.

To scrape later (optional):

```yaml
# infra/prometheus/prometheus.yml — add when core is running:
# - targets: ['api:8000']
#   metrics_path: /metrics
```

## OpenTelemetry decision

**Not added.** Phase 7 uses `trace_id` middleware and structured logs only.
A future path could export OTEL spans from the same event names without changing
the core profile dependencies.

## Tests

```bash
pytest tests/phase7/ -v
```
