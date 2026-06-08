"""Prometheus-compatible metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response

from apps.api.app.observability import events
from apps.api.app.observability.structured_log import log_event
from apps.api.app.core.config import settings
from apps.api.app.reliability.metrics import render_prometheus_text

router = APIRouter(tags=["observability"])


@router.get("/metrics")
def metrics() -> Response:
    """Expose lightweight AXON metrics in Prometheus text format."""
    body = render_prometheus_text()
    log_event(
        level="debug",
        service=settings.service_name,
        event=events.METRICS_SNAPSHOT_GENERATED,
        message="Metrics snapshot generated",
        status="ok",
        component="metrics",
    )
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")
