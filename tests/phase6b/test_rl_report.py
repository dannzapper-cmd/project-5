"""Phase 6B RL report-schema, reproducibility, MLflow, and runner tests.

Uses the tiny CI profile so the full RL suite stays under the 2-minute budget.

Synthetic RL operational policy. No real patient data. No medical decisions.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("numpy")
pytest.importorskip("gymnasium")
pytest.importorskip("stable_baselines3")
pytest.importorskip("torch")

from apps.learning.rl.experiment import run_rl_experiment  # noqa: E402

REQUIRED_FIELDS = {
    "experiment_id",
    "timestamp_utc",
    "seed",
    "env_name",
    "algorithm",
    "total_timesteps_or_episodes",
    "observation_dim",
    "action_count",
    "reward_version",
    "baseline_reward",
    "trained_policy_reward",
    "mean_reward",
    "unsafe_action_rate",
    "hitl_suggestion_rate",
    "mlflow_run_id",
    "disclaimer",
}

EXACT_DISCLAIMER = (
    "Synthetic RL operational policy. No real patient data. No medical decisions. "
    "Human review required for high-risk actions."
)


@pytest.fixture(autouse=True)
def _ci_mode(monkeypatch):
    monkeypatch.setenv("RL_CI_MODE", "true")


def test_report_schema_complete():
    report = run_rl_experiment(seed=42)
    report.pop("_model", None)
    missing = REQUIRED_FIELDS - set(report)
    assert not missing, f"missing report fields: {missing}"
    assert report["env_name"] == "AxonTriageEnvV1"
    assert report["reward_version"] == "REWARD_V1"
    assert report["observation_dim"] == 10
    assert report["action_count"] == 6
    assert report["disclaimer"] == EXACT_DISCLAIMER
    assert isinstance(report["mlflow_run_id"], (str, type(None)))


def test_report_metric_types_and_ranges():
    report = run_rl_experiment(seed=42)
    report.pop("_model", None)
    assert isinstance(report["baseline_reward"], float)
    assert isinstance(report["trained_policy_reward"], float)
    assert 0.0 <= report["unsafe_action_rate"] <= 1.0
    assert 0.0 <= report["hitl_suggestion_rate"] <= 1.0


def test_experiment_reproducible_same_seed():
    a = run_rl_experiment(seed=42)
    b = run_rl_experiment(seed=42)
    a.pop("_model", None)
    b.pop("_model", None)
    volatile = {"experiment_id", "timestamp_utc", "mlflow_run_id"}
    a = {k: v for k, v in a.items() if k not in volatile}
    b = {k: v for k, v in b.items() if k not in volatile}
    assert a["trained_policy_reward"] == b["trained_policy_reward"]
    assert a["baseline_reward"] == b["baseline_reward"]


def test_experiment_differs_with_different_seed():
    a = run_rl_experiment(seed=42)
    b = run_rl_experiment(seed=123)
    # Different seeds should not give identical trained rewards (tiny chance).
    assert a["trained_policy_reward"] != b["trained_policy_reward"]


def test_mlflow_logs_locally_without_server(tmp_path, monkeypatch):
    pytest.importorskip("mlflow")
    import mlflow
    from apps.learning.rl import mlflow_utils

    tracking = tmp_path / "mlruns"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking.resolve().as_uri())

    report = run_rl_experiment(seed=42)
    report.pop("_model", None)
    run_id = mlflow_utils.log_rl_run(report, artifacts=[])
    assert run_id is not None

    mlflow.set_tracking_uri(tracking.resolve().as_uri())
    run = mlflow.get_run(run_id)
    assert run.data.params["env_name"] == "AxonTriageEnvV1"
    assert run.data.params["reward_version"] == "REWARD_V1"
    assert "trained_policy_reward" in run.data.metrics


def test_runner_persists_artifacts(tmp_path, monkeypatch):
    from apps.learning.rl import config, runner

    paths = {
        "RL_ARTIFACTS": tmp_path,
        "LATEST_REPORT_PATH": tmp_path / "rl_report.json",
        "STATUS_PATH": tmp_path / "status.json",
        "REWARD_CURVE_JSON_PATH": tmp_path / "reward_curve.json",
        "REWARD_CURVE_CSV_PATH": tmp_path / "reward_curve.csv",
        "POLICY_SUMMARY_PATH": tmp_path / "policy_summary.json",
        "SAFETY_ENVELOPE_PATH": tmp_path / "safety_envelope.md",
        "POLICY_MODEL_PATH": tmp_path / "policy.zip",
        "RUNS_DIR": tmp_path / "runs",
    }
    for name, value in paths.items():
        monkeypatch.setattr(config, name, value)
        monkeypatch.setattr(runner, name, value)

    report = runner.run_and_persist(seed=42, log_mlflow=False, save_policy=False)
    assert (tmp_path / "rl_report.json").exists()
    assert (tmp_path / "reward_curve.csv").exists()
    assert (tmp_path / "policy_summary.json").exists()
    assert (tmp_path / "safety_envelope.md").exists()
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["status"] == "completed"
    assert report["mlflow_run_id"] is None
    # Safety envelope contains the exact disclaimer.
    assert EXACT_DISCLAIMER in (tmp_path / "safety_envelope.md").read_text()
