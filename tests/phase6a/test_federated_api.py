"""Phase 6A federated learning API + safety tests.

These tests intentionally do NOT import Flower/torch so they run in core CI
(which does not install the learning profile dependencies). They validate the
versioned V1 API contract, the idle-before-run behaviour, and the
no-real-data/no-medical-claims safety boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from apps.api.main import app
from fastapi.testclient import TestClient

FED_PKG = Path(__file__).resolve().parents[2] / "apps" / "learning" / "federated"


@pytest.fixture
def client():
    return TestClient(app)


def _point_service_at(tmp_path, monkeypatch):
    """Point the learning service at an empty temp artifacts dir (idle state)."""
    monkeypatch.setattr(
        "apps.api.app.learning.service.LATEST_REPORT_PATH",
        tmp_path / "federated_report.json",
    )
    monkeypatch.setattr(
        "apps.api.app.learning.service.STATUS_PATH", tmp_path / "status.json"
    )
    monkeypatch.setattr(
        "apps.api.app.learning.service.LEARNING_ARTIFACTS", tmp_path
    )


def test_status_idle_before_run(client, tmp_path, monkeypatch):
    _point_service_at(tmp_path, monkeypatch)
    res = client.get("/api/learning/federated/status")
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "v1"
    assert data["status"] == "idle"
    assert data["has_run"] is False
    assert data["latest_global_accuracy"] is None
    assert "No real patient data" in data["disclaimer"]
    assert "No medical claims" in data["disclaimer"]


def test_latest_idle_before_run(client, tmp_path, monkeypatch):
    _point_service_at(tmp_path, monkeypatch)
    res = client.get("/api/learning/federated/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "v1"
    assert data["has_run"] is False
    assert data["global_results"] == []


def test_status_completed_after_run(client, tmp_path, monkeypatch):
    """A synthetic completed report yields a populated, schema-valid status."""
    report = {
        "experiment_id": "fl-test123",
        "timestamp_utc": "2026-06-07T00:00:00+00:00",
        "seed": 42,
        "num_clients": 3,
        "num_rounds": 2,
        "local_epochs": 2,
        "model_type": "AxonFLModelV1",
        "model_param_count": 850,
        "framework": "flower==1.30.0",
        "strategy": "FedAvg",
        "global_results": [
            {"round": 1, "global_loss": 0.6, "global_accuracy": 0.7},
            {"round": 2, "global_loss": 0.4, "global_accuracy": 0.85},
        ],
        "final_global_loss": 0.4,
        "final_global_accuracy": 0.85,
        "client_summaries": [
            {
                "client_id": "edge-client-01",
                "data_size": 100,
                "signal_type": "emg_fatigue_noise",
                "final_local_loss": 0.42,
                "final_local_accuracy": 0.8,
                "anomaly_ratio": 0.4,
            }
        ],
        "mlflow_run_id": "abc123",
        "disclaimer": (
            "Synthetic federated learning simulation. "
            "No real patient data. No medical claims."
        ),
    }
    (tmp_path / "federated_report.json").write_text(json.dumps(report))
    _point_service_at(tmp_path, monkeypatch)

    res = client.get("/api/learning/federated/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["has_run"] is True
    assert data["num_clients"] == 3
    assert data["completed_rounds"] == 2
    assert data["latest_global_accuracy"] == 0.85
    assert data["mlflow_run_id"] == "abc123"
    assert len(data["client_summaries"]) == 1
    assert len(data["convergence"]) == 2


def test_history_endpoint(client, tmp_path, monkeypatch):
    _point_service_at(tmp_path, monkeypatch)
    res = client.get("/api/learning/federated/history")
    assert res.status_code == 200
    assert res.json()["synthetic_only"] is True


def test_no_real_data_paths_in_federated_package():
    """No network/download/clinical-dataset access in the FL package source."""
    forbidden = ("requests.get", "urllib", "http://", "https://", "kaggle", "physionet")
    for py in FED_PKG.glob("*.py"):
        text = py.read_text().lower()
        for token in forbidden:
            assert token.lower() not in text, f"forbidden token {token!r} in {py.name}"


def test_data_module_declares_synthetic_only():
    data_src = (FED_PKG / "data.py").read_text()
    assert "SYNTHETIC ONLY" in data_src
    assert "No real patient data" in data_src
