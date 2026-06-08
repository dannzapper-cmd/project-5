"""Phase 6A federated learning engine tests (Flower + torch required).

These are skipped automatically when the learning-profile dependencies are not
installed (e.g. core CI), and run locally after ``make learning-install``.

Fixtures are intentionally tiny (2 clients, 1 round, 1 epoch, 50 samples) so the
full FL suite stays well under the 2-minute budget and each test under 30s.

Synthetic federated learning simulation. No real patient data. No medical claims.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("flwr")

from apps.learning.federated.config import (  # noqa: E402
    CLIENT_REGISTRY,
    MIN_CLIENTS,
    client_specs,
)
from apps.learning.federated.data import (  # noqa: E402
    build_client_datasets,
    generate_client_dataset,
)
from apps.learning.federated.model import (  # noqa: E402
    AxonFLModelV1,
    count_parameters,
    evaluate,
    train_local,
)
from apps.learning.federated.simulation import run_federated_experiment  # noqa: E402

SMOKE = dict(num_clients=2, num_rounds=1, local_epochs=1, seed=42, dataset_size=50)


# --- synthetic data -------------------------------------------------------
def test_three_plus_production_clients_available():
    assert len(CLIENT_REGISTRY) >= 3
    assert MIN_CLIENTS == 3
    specs = client_specs(3)
    assert len(specs) == 3
    assert {s["client_id"] for s in specs} == {
        "edge-client-01",
        "edge-client-02",
        "edge-client-03",
    }


def test_data_deterministic_with_seed():
    a = generate_client_dataset(
        client_id="c", client_index=1, signal_type="emg_fatigue_noise",
        description="d", data_size=60, anomaly_ratio=0.4, base_seed=42,
    )
    b = generate_client_dataset(
        client_id="c", client_index=1, signal_type="emg_fatigue_noise",
        description="d", data_size=60, anomaly_ratio=0.4, base_seed=42,
    )
    np.testing.assert_array_equal(a.features, b.features)
    np.testing.assert_array_equal(a.labels, b.labels)


def test_data_changes_with_seed():
    a = generate_client_dataset(
        client_id="c", client_index=1, signal_type="emg_fatigue_noise",
        description="d", data_size=60, anomaly_ratio=0.4, base_seed=42,
    )
    b = generate_client_dataset(
        client_id="c", client_index=1, signal_type="emg_fatigue_noise",
        description="d", data_size=60, anomaly_ratio=0.4, base_seed=7,
    )
    assert not np.array_equal(a.features, b.features)


def test_client_distributions_are_distinct():
    datasets = build_client_datasets(client_specs(4), base_seed=42)
    means = [ds.features.mean(axis=0) for ds in datasets]
    # Every pair of clients must differ meaningfully in mean feature vector.
    for i in range(len(means)):
        for j in range(i + 1, len(means)):
            assert np.linalg.norm(means[i] - means[j]) > 0.05


def test_labels_include_both_classes():
    datasets = build_client_datasets(client_specs(3), base_seed=42)
    for ds in datasets:
        classes = set(np.unique(ds.labels).tolist())
        assert classes == {0, 1}


# --- model ----------------------------------------------------------------
def test_model_parameter_count_under_1000():
    assert count_parameters(AxonFLModelV1()) == 850
    assert count_parameters(AxonFLModelV1()) < 1000


def test_local_training_smoke_reduces_loss():
    ds = generate_client_dataset(
        client_id="c", client_index=1, signal_type="emg_fatigue_noise",
        description="d", data_size=120, anomaly_ratio=0.4, base_seed=42,
    )
    model = AxonFLModelV1()
    loss0, _ = evaluate(model, ds.features, ds.labels)
    train_local(model, ds.features, ds.labels, epochs=20, lr=0.1, seed=42)
    loss1, acc1 = evaluate(model, ds.features, ds.labels)
    assert loss1 < loss0


# --- Flower FedAvg simulation ---------------------------------------------
def test_flower_fedavg_smoke_runs():
    report = run_federated_experiment(**SMOKE)
    assert report["strategy"] == "FedAvg"
    assert report["framework"].startswith("flower==")
    assert report["num_clients"] == 2
    assert len(report["client_summaries"]) == 2


def test_report_schema_complete():
    report = run_federated_experiment(**SMOKE)
    required = {
        "experiment_id",
        "timestamp_utc",
        "seed",
        "num_clients",
        "num_rounds",
        "local_epochs",
        "model_type",
        "global_results",
        "client_summaries",
        "mlflow_run_id",
        "disclaimer",
    }
    assert required.issubset(report.keys())
    assert report["model_type"] == "AxonFLModelV1"
    assert report["disclaimer"] == (
        "Synthetic federated learning simulation. No real patient data. No medical claims."
    )
    for r in report["global_results"]:
        assert {"round", "global_loss", "global_accuracy"}.issubset(r.keys())
    for c in report["client_summaries"]:
        assert {"client_id", "data_size", "signal_type", "final_local_loss"}.issubset(c.keys())


def test_experiment_reproducible_same_seed():
    a = run_federated_experiment(**SMOKE)
    b = run_federated_experiment(**SMOKE)
    assert a["global_results"] == b["global_results"]
    assert a["final_global_loss"] == b["final_global_loss"]


def test_default_run_converges():
    """Loss should decrease from first to last round with default-ish params."""
    report = run_federated_experiment(
        num_clients=4, num_rounds=5, local_epochs=3, seed=42
    )
    rounds = report["global_results"]
    assert rounds[-1]["global_loss"] < rounds[0]["global_loss"]


# --- MLflow local file store ----------------------------------------------
def test_mlflow_logs_locally_without_server(tmp_path, monkeypatch):
    pytest.importorskip("mlflow")
    import mlflow
    from apps.learning.federated import mlflow_utils

    tracking = tmp_path / "mlruns"

    monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking.resolve().as_uri())
    report = run_federated_experiment(**SMOKE)
    run_id = mlflow_utils.log_federated_run(report, artifacts=[])
    assert run_id is not None
    mlflow.set_tracking_uri(tracking.resolve().as_uri())
    run = mlflow.get_run(run_id)
    assert run.data.params["model_type"] == "AxonFLModelV1"
    assert "global_accuracy" in run.data.metrics


# --- runner persistence ----------------------------------------------------
def test_runner_persists_artifacts(tmp_path, monkeypatch):
    from apps.learning.federated import config, runner

    monkeypatch.setattr(config, "LEARNING_ARTIFACTS", tmp_path)
    monkeypatch.setattr(config, "LATEST_REPORT_PATH", tmp_path / "federated_report.json")
    monkeypatch.setattr(config, "STATUS_PATH", tmp_path / "status.json")
    monkeypatch.setattr(
        config, "CLIENT_DISTRIBUTION_PATH", tmp_path / "client_distribution_summary.json"
    )
    monkeypatch.setattr(config, "CONVERGENCE_JSON_PATH", tmp_path / "convergence.json")
    monkeypatch.setattr(config, "CONVERGENCE_CSV_PATH", tmp_path / "convergence.csv")
    monkeypatch.setattr(config, "MODEL_CARD_PATH", tmp_path / "model_card.md")
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path / "runs")
    for name in [
        "LEARNING_ARTIFACTS",
        "LATEST_REPORT_PATH",
        "STATUS_PATH",
        "CLIENT_DISTRIBUTION_PATH",
        "CONVERGENCE_JSON_PATH",
        "CONVERGENCE_CSV_PATH",
        "MODEL_CARD_PATH",
        "RUNS_DIR",
    ]:
        monkeypatch.setattr(runner, name, getattr(config, name))

    report = runner.run_and_persist(log_mlflow=False, **SMOKE)
    assert (tmp_path / "federated_report.json").exists()
    assert (tmp_path / "convergence.csv").exists()
    assert (tmp_path / "client_distribution_summary.json").exists()
    status = (tmp_path / "status.json").read_text()
    assert "completed" in status
    assert report["mlflow_run_id"] is None
