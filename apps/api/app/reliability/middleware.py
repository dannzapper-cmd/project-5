"""Phase 7 request middleware: trace_id propagation and request counters."""

from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from apps.api.app.reliability.metrics import api_metrics


class TraceAndMetricsMiddleware(BaseHTTPMiddleware):
    """Attach trace_id to each request and count requests/errors."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        request.state.trace_id = trace_id
        api_metrics.inc_request()
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        if response.status_code >= 500:
            api_metrics.inc_error()
        return response
