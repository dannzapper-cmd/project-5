"""Read the latest federated run artifacts and build versioned API payloads.

The status endpoint must work before any run (idle, null metrics, disclaimer
present) and after a run (completed, populated metrics). All reads are defensive:
missing/corrupt files degrade to a safe idle state.

Synthetic federated learning simulation. No real patient data. No medical claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.api.app.schemas.learning import (
    ClientSummaryV1,
    FederatedResultV1,
    FederatedRunSummaryV1,
    FederatedStatusV1,
    GlobalRoundResultV1,
)
from apps.learning.federated.config import (
    LATEST_REPORT_PATH,
    LEARNING_ARTIFACTS,
    STATUS_PATH,
)


def _safe_read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _client_summaries(report: dict) -> list[ClientSummaryV1]:
    out = []
    for c in report.get("client_summaries", []):
        out.append(
            ClientSummaryV1(
                client_id=c.get("client_id", "unknown"),
                data_size=int(c.get("data_size", 0)),
                signal_type=c.get("signal_type", "unknown"),
                final_local_loss=float(c.get("final_local_loss", 0.0)),
                final_local_accuracy=c.get("final_local_accuracy"),
                anomaly_ratio=c.get("anomaly_ratio"),
            )
        )
    return out


def _convergence(report: dict) -> list[GlobalRoundResultV1]:
    return [
        GlobalRoundResultV1(
            round=int(r["round"]),
            global_loss=float(r["global_loss"]),
            global_accuracy=float(r["global_accuracy"]),
        )
        for r in report.get("global_results", [])
    ]


def _summary(report: dict) -> FederatedRunSummaryV1:
    rounds = report.get("global_results", [])
    return FederatedRunSummaryV1(
        experiment_id=report.get("experiment_id"),
        timestamp_utc=report.get("timestamp_utc"),
        seed=report.get("seed"),
        num_clients=int(report.get("num_clients", 0)),
        num_rounds=int(report.get("num_rounds", 0)),
        local_epochs=report.get("local_epochs"),
        model_type=report.get("model_type"),
        model_param_count=report.get("model_param_count"),
        framework=report.get("framework"),
        strategy=report.get("strategy"),
        final_global_loss=report.get("final_global_loss"),
        final_global_accuracy=report.get("final_global_accuracy"),
        completed_rounds=max((int(r["round"]) for r in rounds), default=0),
        mlflow_run_id=report.get("mlflow_run_id"),
        report_path=str(LATEST_REPORT_PATH),
    )


def _resolve_status(report: dict | None, status_doc: dict | None) -> str:
    if status_doc and status_doc.get("status"):
        return str(status_doc["status"])
    return "completed" if report else "idle"


def get_federated_status() -> FederatedStatusV1:
    """Build the FederatedStatusV1 payload (idle when no run exists)."""
    report = _safe_read_json(LATEST_REPORT_PATH)
    status_doc = _safe_read_json(STATUS_PATH)
    status = _resolve_status(report, status_doc)

    if report is None:
        return FederatedStatusV1(
            status=status,  # type: ignore[arg-type]
            has_run=False,
            artifact_dir=str(LEARNING_ARTIFACTS),
        )

    summary = _summary(report)
    convergence = _convergence(report)
    latest = convergence[-1] if convergence else None
    return FederatedStatusV1(
        status=status,  # type: ignore[arg-type]
        has_run=True,
        num_clients=summary.num_clients,
        num_rounds=summary.num_rounds,
        completed_rounds=summary.completed_rounds,
        latest_global_loss=latest.global_loss if latest else None,
        latest_global_accuracy=latest.global_accuracy if latest else None,
        summary=summary,
        client_summaries=_client_summaries(report),
        convergence=convergence,
        mlflow_run_id=report.get("mlflow_run_id"),
        report_path=str(LATEST_REPORT_PATH),
        artifact_dir=str(LEARNING_ARTIFACTS),
    )


def get_federated_result() -> FederatedResultV1:
    """Build the full FederatedResultV1 payload (idle when no run exists)."""
    report = _safe_read_json(LATEST_REPORT_PATH)
    status_doc = _safe_read_json(STATUS_PATH)
    status = _resolve_status(report, status_doc)

    if report is None:
        return FederatedResultV1(status=status, has_run=False)  # type: ignore[arg-type]

    return FederatedResultV1(
        status=status,  # type: ignore[arg-type]
        has_run=True,
        summary=_summary(report),
        global_results=_convergence(report),
        client_summaries=_client_summaries(report),
        client_distribution_summary=report.get("client_distribution_summary"),
    )


def get_history(limit: int = 20) -> dict[str, Any]:
    """Lightweight history view from the per-run artifacts directory."""
    runs_dir = LEARNING_ARTIFACTS / "runs"
    runs: list[dict] = []
    if runs_dir.exists():
        for path in sorted(runs_dir.glob("*.json"), reverse=True)[:limit]:
            doc = _safe_read_json(path)
            if doc:
                runs.append(
                    {
                        "experiment_id": doc.get("experiment_id"),
                        "timestamp_utc": doc.get("timestamp_utc"),
                        "final_global_accuracy": doc.get("final_global_accuracy"),
                        "final_global_loss": doc.get("final_global_loss"),
                        "mlflow_run_id": doc.get("mlflow_run_id"),
                    }
                )
    return {"runs": runs, "synthetic_only": True}
