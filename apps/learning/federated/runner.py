"""Persist a federated experiment: run -> artifacts -> MLflow -> status.

This module is the integration point used by the CLI script
(``scripts/run_federated_learning.py``) and the Docker ``fl-runner`` service. It
writes the evidence artifacts the dashboard/API and the Evidence Center read.

Synthetic federated learning simulation. No real patient data. No medical claims.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.learning.federated.config import (
    CLIENT_DISTRIBUTION_PATH,
    CONVERGENCE_CSV_PATH,
    CONVERGENCE_JSON_PATH,
    LATEST_REPORT_PATH,
    LEARNING_ARTIFACTS,
    MODEL_CARD_PATH,
    RUNS_DIR,
    STATUS_PATH,
)
from apps.learning.federated.disclaimer import DISCLAIMER, SAFETY_SCOPE
from apps.learning.federated.mlflow_utils import log_federated_run
from apps.learning.federated.simulation import run_federated_experiment


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def write_status(status: str, extra: dict | None = None) -> None:
    """Write a lightweight idle/running/completed/failed status marker."""
    payload = {
        "status": status,
        "updated_utc": datetime.now(UTC).isoformat(),
        "disclaimer": DISCLAIMER,
    }
    if extra:
        payload.update(extra)
    _write_json(STATUS_PATH, payload)


def _write_convergence(report: dict) -> None:
    rounds = report["global_results"]
    _write_json(CONVERGENCE_JSON_PATH, {"rounds": rounds, "disclaimer": DISCLAIMER})
    CONVERGENCE_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONVERGENCE_CSV_PATH.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["round", "global_loss", "global_accuracy"])
        for r in rounds:
            writer.writerow([r["round"], r["global_loss"], r["global_accuracy"]])


def _write_model_card(report: dict) -> None:
    card = f"""# Model / Data Card — AxonFLModelV1 (Phase 6A federated simulation)

> {DISCLAIMER}

{SAFETY_SCOPE}

## Model
- Type: `{report['model_type']}` (tiny MLP, input_dim=8, hidden=[32, 16], output=2)
- Trainable parameters: {report['model_param_count']}
- Framework: {report['framework']} / strategy: {report['strategy']}

## Federated run
- Clients (simulated edge nodes): {report['num_clients']}
- Rounds: {report['num_rounds']} | Local epochs: {report['local_epochs']} | Seed: {report['seed']}
- Final global loss: {report['final_global_loss']}
- Final global accuracy: {report['final_global_accuracy']}

## Data
- Synthetic, non-IID, biosignal-like features only (EMG/ECG/IMU/SpO2 proxies).
- No real patient data. No clinical datasets. No diagnostic validity implied.
"""
    MODEL_CARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CARD_PATH.write_text(card)


def run_and_persist(
    *,
    num_clients: int = 3,
    num_rounds: int = 5,
    local_epochs: int = 3,
    seed: int = 42,
    learning_rate: float = 0.05,
    dataset_size: int | None = None,
    log_mlflow: bool = True,
    num_cpus: int = 1,
) -> dict:
    """Run the experiment, write all artifacts, optionally log MLflow."""
    LEARNING_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    write_status("running", {"num_clients": num_clients, "num_rounds": num_rounds})
    try:
        report = run_federated_experiment(
            num_clients=num_clients,
            num_rounds=num_rounds,
            local_epochs=local_epochs,
            seed=seed,
            learning_rate=learning_rate,
            dataset_size=dataset_size,
            num_cpus=num_cpus,
        )

        _write_json(CLIENT_DISTRIBUTION_PATH, report["client_distribution_summary"])
        _write_convergence(report)

        artifacts = [
            LATEST_REPORT_PATH,
            CLIENT_DISTRIBUTION_PATH,
            CONVERGENCE_JSON_PATH,
            CONVERGENCE_CSV_PATH,
            MODEL_CARD_PATH,
        ]
        # Write the report once (without run id) so MLflow can log it, then
        # rewrite with the run id linked.
        _write_json(LATEST_REPORT_PATH, report)
        _write_model_card(report)

        run_id = log_federated_run(report, artifacts) if log_mlflow else None
        report["mlflow_run_id"] = run_id
        _write_json(LATEST_REPORT_PATH, report)
        _write_json(RUNS_DIR / f"{report['experiment_id']}.json", report)

        write_status(
            "completed",
            {
                "num_clients": num_clients,
                "num_rounds": num_rounds,
                "final_global_loss": report["final_global_loss"],
                "final_global_accuracy": report["final_global_accuracy"],
                "mlflow_run_id": run_id,
                "report_path": str(LATEST_REPORT_PATH),
            },
        )
        return report
    except Exception as exc:  # noqa: BLE001
        write_status("failed", {"error": str(exc)})
        raise
