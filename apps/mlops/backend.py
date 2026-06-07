"""MLOps tracking backend abstraction (local default, MLflow optional)."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path

from apps.mlops.config import AXON_MLOPS_BACKEND
from apps.mlops.registry import write_registry_atomic


class MLOpsBackend(ABC):
    @abstractmethod
    def log_params(self, params: dict) -> None: ...

    @abstractmethod
    def log_metrics(self, metrics: dict) -> None: ...

    @abstractmethod
    def log_artifact(self, path: str) -> None: ...

    @abstractmethod
    def end_run(self) -> None: ...


class LocalMLOpsBackend(MLOpsBackend):
    """Writes params and metrics as JSON alongside artifacts. Always available."""

    def __init__(self, run_dir: str) -> None:
        self._dir = Path(run_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._params: dict = {}
        self._metrics: dict = {}

    def log_params(self, params: dict) -> None:
        self._params.update(params)
        write_registry_atomic(self._params, self._dir / "params.json")

    def log_metrics(self, metrics: dict) -> None:
        self._metrics.update(metrics)
        write_registry_atomic(self._metrics, self._dir / "metrics.json")

    def log_artifact(self, path: str) -> None:
        pass

    def end_run(self) -> None:
        pass


class MLflowBackend(MLOpsBackend):
    def __init__(self, tracking_uri: str, experiment_name: str) -> None:
        try:
            import mlflow
        except ImportError as exc:
            raise RuntimeError("mlflow not installed. Set AXON_MLOPS_BACKEND=local.") from exc
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        mlflow.start_run()
        self._mlflow = mlflow

    def log_params(self, params: dict) -> None:
        self._mlflow.log_params(params)

    def log_metrics(self, metrics: dict) -> None:
        self._mlflow.log_metrics(metrics)

    def log_artifact(self, path: str) -> None:
        self._mlflow.log_artifact(path)

    def end_run(self) -> None:
        self._mlflow.end_run()


def get_mlops_backend(run_dir: str) -> MLOpsBackend:
    if AXON_MLOPS_BACKEND == "mlflow":
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./artifacts/mlops/mlruns")
        return MLflowBackend(tracking_uri, "axon-phase4")
    return LocalMLOpsBackend(run_dir)
