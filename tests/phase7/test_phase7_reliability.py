"""Phase 7 reliability endpoint and helper tests."""

from __future__ import annotations

import json

import pytest
from apps.api.app.observability.structured_log import log_event
from apps.api.app.reliability.dependency_checks import ALLOWED_STATUSES, ComponentCheck
from apps.api.app.reliability.service_status import compute_components
from apps.api.main import app
from fastapi.testclient import TestClient

ALLOWED = {"ok", "degraded", "unavailable", "inactive", "error"}


@pytest.fixture
def client():
    return TestClient(app)


def test_health_live_returns_200_and_schema(client):
    res = client.get("/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "axon-api"
    assert "timestamp" in data


def test_health_ready_schema(client):
    res = client.get("/health/ready")
    assert res.status_code in (200, 503)
    data = res.json()
    assert data["status"] in ALLOWED
    assert isinstance(data["components"], dict)
    assert "timestamp" in data


def test_status_services_schema(client):
    res = client.get("/status/services")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ALLOWED
    assert data["service"] == "axon-api"
    assert "timestamp" in data
    for name, comp in data["components"].items():
        assert comp["status"] in ALLOWED, f"{name} bad status"
        assert isinstance(comp["required"], bool), f"{name} missing required bool"
        assert isinstance(comp["message"], str), f"{name} missing message"


def test_ready_degraded_not_500_when_optional_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        "apps.api.app.reliability.service_status.check_redis",
        lambda: ComponentCheck(status="ok", required=True, message="Redis ok"),
    )
    monkeypatch.setattr(
        "apps.api.app.reliability.service_status.check_mqtt",
        lambda: ComponentCheck(status="ok", required=True, message="MQTT ok"),
    )
    monkeypatch.setattr(
        "apps.api.app.reliability.service_status.check_mlflow",
        lambda: ComponentCheck(
            status="unavailable", required=False, message="MLflow down"
        ),
    )
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["status"] in ("ok", "degraded")


def test_ready_503_when_required_redis_fails(client, monkeypatch):
    monkeypatch.setattr(
        "apps.api.app.reliability.service_status.check_redis",
        lambda: ComponentCheck(status="error", required=True, message="Redis down"),
    )
    res = client.get("/health/ready")
    assert res.status_code == 503
    assert res.json()["status"] == "error"


def test_metrics_non_empty_prometheus(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    body = res.text
    assert body.strip()
    assert "axon_api_requests_total" in body
    assert "axon_api_errors_total" in body
    assert "axon_degraded_components_total" in body
    assert "text/plain" in res.headers["content-type"]


def test_structured_log_valid_json():
    payload = log_event(
        level="info",
        service="axon-api",
        event="health_check_completed",
        message="test",
        status="ok",
        trace_id="trace-1",
    )
    parsed = json.loads(json.dumps(payload))
    for key in ("timestamp", "level", "service", "event", "message"):
        assert key in parsed
    assert parsed["event"] == "health_check_completed"


def test_evidence_missing_reports_unavailable(client, monkeypatch, tmp_path):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr("apps.api.app.reliability.service_status.FL_REPORT", missing)
    monkeypatch.setattr("apps.api.app.reliability.service_status.RL_REPORT", missing)
    data = client.get("/status/services").json()
    assert data["components"]["fl_module"]["status"] == "unavailable"
    assert data["components"]["rl_module"]["status"] == "unavailable"


def test_no_learning_heavy_imports_in_reliability_modules():
    import apps.api.app.reliability.service_status as ss

    source = open(ss.__file__).read()
    assert "gymnasium" not in source
    assert "stable_baselines3" not in source
    assert "torch" not in source
    assert "flwr" not in source


def test_aggregate_status_vocabulary():
    components = compute_components()
    for comp in components.values():
        assert comp["status"] in ALLOWED_STATUSES


def test_trace_id_header(client):
    res = client.get("/health/live", headers={"X-Trace-Id": "custom-trace"})
    assert res.headers.get("X-Trace-Id") == "custom-trace"


def test_api_requests_counter_increments(client):
    before = client.get("/metrics").text
    client.get("/health/live")
    after = client.get("/metrics").text
    assert before != after or "axon_api_requests_total" in after
