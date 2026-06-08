"""Phase 6B RL API + dependency-isolation tests.

These tests intentionally do NOT import gymnasium / Stable-Baselines3 / torch so
they run in core CI (which does not install the learning profile dependencies).
They validate the versioned V1 API contract, the idle-before-run behaviour, and
the no-real-data / no-medical-claims safety boundary.

Synthetic RL operational policy. No real patient data. No medical decisions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from apps.api.main import app
from fastapi.testclient import TestClient

EXACT_DISCLAIMER = (
    "Synthetic RL operational policy. No real patient data. No medical decisions. "
    "Human review required for high-risk actions."
)


@pytest.fixture
def client():
    return TestClient(app)


def _point_service_at(tmp_path, monkeypatch):
    """Point the RL service at an empty temp artifacts dir (idle state)."""
    monkeypatch.setattr(
        "apps.api.app.learning.rl_service.LATEST_REPORT_PATH",
        tmp_path / "rl_report.json",
    )
    monkeypatch.setattr(
        "apps.api.app.learning.rl_service.STATUS_PATH", tmp_path / "status.json"
    )
    monkeypatch.setattr("apps.api.app.learning.rl_service.RL_ARTIFACTS", tmp_path)


def test_status_idle_before_run(client, tmp_path, monkeypatch):
    _point_service_at(tmp_path, monkeypatch)
    res = client.get("/api/learning/rl/status")
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "v1"
    assert data["status"] == "idle"
    assert data["has_run"] is False
    assert data["trained_policy_reward"] is None
    assert data["disclaimer"] == EXACT_DISCLAIMER


def test_latest_idle_before_run(client, tmp_path, monkeypatch):
    _point_service_at(tmp_path, monkeypatch)
    res = client.get("/api/learning/rl/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "v1"
    assert data["has_run"] is False
    assert data["reward_curve"] == []


def test_status_completed_after_run(client, tmp_path, monkeypatch):
    report = {
        "experiment_id": "rl-test123",
        "timestamp_utc": "2026-06-08T00:00:00+00:00",
        "seed": 42,
        "env_name": "AxonTriageEnvV1",
        "algorithm": "PPO (Stable-Baselines3)",
        "total_timesteps_or_episodes": 15000,
        "observation_dim": 10,
        "observation_names": ["risk_score"],
        "action_count": 6,
        "action_names": ["keep_normal"],
        "reward_version": "REWARD_V1",
        "safety_mode": "synthetic_operational_triage_hitl_required",
        "baseline_reward": 0.82,
        "trained_policy_reward": 79.35,
        "mean_reward": 79.35,
        "policy_improvement_ratio": 95.7,
        "unsafe_action_rate": 0.0,
        "hitl_suggestion_rate": 0.33,
        "episode_length_mean": 170.0,
        "reward_curve": [{"timesteps": 512, "mean_episode_reward": 10.0}],
        "mlflow_run_id": "abc123",
        "disclaimer": EXACT_DISCLAIMER,
    }
    (tmp_path / "rl_report.json").write_text(json.dumps(report))
    _point_service_at(tmp_path, monkeypatch)

    res = client.get("/api/learning/rl/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["has_run"] is True
    assert data["env_name"] == "AxonTriageEnvV1"
    assert data["trained_policy_reward"] == 79.35
    assert data["baseline_reward"] == 0.82
    assert data["hitl_suggestion_rate"] == 0.33
    assert data["mlflow_run_id"] == "abc123"
    assert data["policy_summary"]["reward_version"] == "REWARD_V1"

    latest = client.get("/api/learning/rl/latest").json()
    assert latest["has_run"] is True
    assert len(latest["reward_curve"]) == 1


def test_history_endpoint(client, tmp_path, monkeypatch):
    _point_service_at(tmp_path, monkeypatch)
    res = client.get("/api/learning/rl/history")
    assert res.status_code == 200
    assert res.json()["synthetic_only"] is True


def test_api_imports_without_learning_deps():
    """The core API must import without gymnasium / SB3 / torch (isolation)."""
    code = (
        "import sys; "
        "sys.modules['stable_baselines3'] = None; "
        "sys.modules['gymnasium'] = None; "
        "sys.modules['torch'] = None; "
        "from apps.api.main import app; "
        "print('OK')"
    )
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
