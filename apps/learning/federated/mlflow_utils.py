"""MLflow logging for the federated experiment (local file store by default).

MLflow logging must work WITHOUT a running MLflow server (item 10). We default
to a local ``file:`` tracking URI so ``mlflow ui`` is optional. If MLflow is not
installed, logging degrades gracefully and returns ``None`` (the experiment and
its JSON/CSV artifacts are still produced).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from apps.learning.federated.config import (
    MLFLOW_DEFAULT_TRACKING_DIR,
    MLFLOW_EXPERIMENT_NAME,
)


def default_tracking_uri() -> str:
    """Local file-based tracking URI (no server required)."""
    uri = os.getenv("MLFLOW_TRACKING_URI")
    if uri:
        return uri
    MLFLOW_DEFAULT_TRACKING_DIR.mkdir(parents=True, exist_ok=True)
    return MLFLOW_DEFAULT_TRACKING_DIR.resolve().as_uri()


def log_federated_run(report: dict[str, Any], artifacts: list[Path]) -> str | None:
    """Log params/metrics/artifacts for a federated run. Returns the run id or None."""
    try:
        import mlflow
    except ImportError:
        return None

    mlflow.set_tracking_uri(default_tracking_uri())
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run() as run:
        mlflow.log_params(
            {
                "num_clients": report["num_clients"],
                "num_rounds": report["num_rounds"],
                "local_epochs": report["local_epochs"],
                "model_type": report["model_type"],
                "seed": report["seed"],
                "learning_rate": report["learning_rate"],
                "strategy": report["strategy"],
                "framework": report["framework"],
            }
        )
        mlflow.log_metric("global_loss", float(report["final_global_loss"]))
        mlflow.log_metric("global_accuracy", float(report["final_global_accuracy"]))
        for entry in report["global_results"]:
            step = int(entry["round"])
            mlflow.log_metric("round_global_loss", float(entry["global_loss"]), step=step)
            mlflow.log_metric("round_global_accuracy", float(entry["global_accuracy"]), step=step)
        for path in artifacts:
            if path.exists():
                mlflow.log_artifact(str(path))
        return run.info.run_id
