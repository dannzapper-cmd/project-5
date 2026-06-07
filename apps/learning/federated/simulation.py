"""Flower (FedAvg) federated learning simulation for AXON Phase 6A.

This is *real* Flower usage: synthetic edge clients are simulated with
``flwr.simulation.start_simulation`` (stable Flower 1.x simulation API) and the
central coordinator aggregates updates with ``flwr.server.strategy.FedAvg``. It
is NOT a manual for-loop pretending to be federated learning.

Determinism: clients start from a shared seeded initialisation, each client
seeds its own RNGs before training, and global metrics are computed centrally
(``evaluate_fn``) on a fixed held-out set so per-round results are reproducible.

Synthetic federated learning simulation. No real patient data. No medical claims.
"""

from __future__ import annotations

import logging
import os
import warnings
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import numpy as np

# Quieten Flower/Ray noise for a clean CLI experience before importing flwr.
warnings.filterwarnings("ignore")
os.environ.setdefault("RAY_DEDUP_LOGS", "1")
os.environ.setdefault("GRPC_VERBOSITY", "NONE")

import flwr as fl  # noqa: E402
from flwr.common import (  # noqa: E402
    Context,
    Metrics,
    ndarrays_to_parameters,
)

from apps.learning.federated.config import (  # noqa: E402
    CLASS_NAMES,
    DEFAULT_LEARNING_RATE,
    DEFAULT_LOCAL_EPOCHS,
    DEFAULT_NUM_ROUNDS,
    DEFAULT_SEED,
    MODEL_TYPE,
    client_specs,
)
from apps.learning.federated.data import (  # noqa: E402
    ClientDataset,
    build_client_datasets,
    distribution_summary,
)
from apps.learning.federated.disclaimer import DISCLAIMER  # noqa: E402
from apps.learning.federated.model import (  # noqa: E402
    AxonFLModelV1,
    count_parameters,
    evaluate,
    get_parameters,
    set_parameters,
    set_seed,
    train_local,
)

logging.getLogger("flwr").setLevel(logging.WARNING)
logging.getLogger("ray").setLevel(logging.ERROR)


def _split_train_eval(
    ds: ClientDataset, eval_fraction: float = 0.25
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic per-client train/eval split (data already shuffled)."""
    n = ds.data_size
    n_eval = max(1, int(round(n * eval_fraction)))
    x_eval, y_eval = ds.features[:n_eval], ds.labels[:n_eval]
    x_train, y_train = ds.features[n_eval:], ds.labels[n_eval:]
    return x_train, y_train, x_eval, y_eval


class AxonFlowerClient(fl.client.NumPyClient):
    """One simulated edge node training :class:`AxonFLModelV1` locally."""

    def __init__(
        self,
        ds: ClientDataset,
        *,
        local_epochs: int,
        lr: float,
        seed: int,
    ) -> None:
        self.ds = ds
        self.local_epochs = local_epochs
        self.lr = lr
        self.seed = seed
        self.model = AxonFLModelV1()
        self.x_train, self.y_train, self.x_eval, self.y_eval = _split_train_eval(ds)

    def get_parameters(self, config):  # noqa: ANN001, ARG002
        return get_parameters(self.model)

    def fit(self, parameters, config):  # noqa: ANN001, ARG002
        set_parameters(self.model, parameters)
        loss = train_local(
            self.model,
            self.x_train,
            self.y_train,
            epochs=self.local_epochs,
            lr=self.lr,
            seed=self.seed,
        )
        metrics: Metrics = {
            "local_loss": float(loss),
            "client_index": float(self.ds.client_index),
        }
        return get_parameters(self.model), len(self.x_train), metrics

    def evaluate(self, parameters, config):  # noqa: ANN001, ARG002
        set_parameters(self.model, parameters)
        loss, accuracy = evaluate(self.model, self.x_eval, self.y_eval)
        return float(loss), len(self.x_eval), {"accuracy": float(accuracy)}


def run_federated_experiment(
    *,
    num_clients: int = 3,
    num_rounds: int = DEFAULT_NUM_ROUNDS,
    local_epochs: int = DEFAULT_LOCAL_EPOCHS,
    seed: int = DEFAULT_SEED,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    dataset_size: int | None = None,
    num_cpus: int = 1,
) -> dict[str, Any]:
    """Run a Flower FedAvg simulation and return the federated report dict.

    ``num_cpus=1`` keeps the Ray backend serial, which is light and keeps the
    per-round aggregation order stable for reproducibility. Pure compute; no
    artifacts are written here (see :mod:`apps.learning.federated.runner`).
    """
    set_seed(seed)

    specs = client_specs(num_clients)
    if dataset_size is not None:
        for spec in specs:
            spec["data_size"] = int(dataset_size)
    datasets = build_client_datasets(specs, base_seed=seed)
    by_index = {ds.client_index: ds for ds in datasets}

    # Held-out global eval set = concatenation of every client's eval partition.
    global_x_parts, global_y_parts = [], []
    for ds in datasets:
        _, _, xe, ye = _split_train_eval(ds)
        global_x_parts.append(xe)
        global_y_parts.append(ye)
    global_x = np.concatenate(global_x_parts, axis=0)
    global_y = np.concatenate(global_y_parts, axis=0)

    # Shared, deterministic initial parameters for all clients.
    init_model = AxonFLModelV1()
    set_seed(seed)
    initial_parameters = ndarrays_to_parameters(get_parameters(init_model))

    convergence: list[dict[str, float]] = []
    final_params_holder: list[list[np.ndarray]] = []

    def evaluate_fn(server_round: int, parameters_ndarrays, config):  # noqa: ANN001, ARG001
        final_params_holder.append(parameters_ndarrays)
        model = AxonFLModelV1()
        set_parameters(model, parameters_ndarrays)
        loss, accuracy = evaluate(model, global_x, global_y)
        convergence.append(
            {
                "round": int(server_round),
                "global_loss": round(float(loss), 6),
                "global_accuracy": round(float(accuracy), 6),
            }
        )
        return float(loss), {"global_accuracy": float(accuracy)}

    def client_fn(context: Context) -> fl.client.Client:
        partition_id = int(context.node_config["partition-id"])
        ds = by_index[specs[partition_id]["client_index"]]
        return AxonFlowerClient(
            ds, local_epochs=local_epochs, lr=learning_rate, seed=seed + ds.client_index
        ).to_client()

    def fit_weighted_avg(metrics: list[tuple[int, Metrics]]) -> Metrics:
        total = sum(n for n, _ in metrics) or 1
        avg = sum(n * float(m.get("local_loss", 0.0)) for n, m in metrics) / total
        return {"mean_local_loss": avg}

    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=num_clients,
        min_evaluate_clients=num_clients,
        min_available_clients=num_clients,
        initial_parameters=initial_parameters,
        evaluate_fn=evaluate_fn,
        fit_metrics_aggregation_fn=fit_weighted_avg,
    )

    history = fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=num_clients,
        config=fl.server.ServerConfig(num_rounds=num_rounds),
        strategy=strategy,
        ray_init_args={
            "include_dashboard": False,
            "num_cpus": num_cpus,
            "log_to_driver": False,
            "ignore_reinit_error": True,
        },
    )

    # Final global parameters -> per-client "final local loss" on full client data.
    final_params = final_params_holder[-1] if final_params_holder else None
    final_model = AxonFLModelV1()
    if final_params is not None:
        set_parameters(final_model, final_params)
    client_summaries = []
    for ds in datasets:
        floss, facc = evaluate(final_model, ds.features, ds.labels)
        client_summaries.append(
            {
                "client_id": ds.client_id,
                "data_size": ds.data_size,
                "signal_type": ds.signal_type,
                "final_local_loss": round(float(floss), 6),
                "final_local_accuracy": round(float(facc), 6),
                "anomaly_ratio": round(ds.anomaly_ratio, 4),
            }
        )

    global_results = sorted(convergence, key=lambda r: r["round"])
    # Drop the round-0 (pre-training) centralized eval that Flower runs; keep
    # rounds 1..num_rounds for the convergence curve, but retain round 0 as the
    # documented baseline if present.
    final = global_results[-1] if global_results else {"global_loss": 0.0, "global_accuracy": 0.0}

    report = {
        "experiment_id": f"fl-{uuid4().hex[:12]}",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "seed": int(seed),
        "num_clients": int(num_clients),
        "num_rounds": int(num_rounds),
        "local_epochs": int(local_epochs),
        "learning_rate": float(learning_rate),
        "model_type": MODEL_TYPE,
        "model_param_count": count_parameters(final_model),
        "class_names": list(CLASS_NAMES),
        "framework": f"flower=={fl.__version__}",
        "strategy": "FedAvg",
        "global_results": [
            {
                "round": r["round"],
                "global_loss": r["global_loss"],
                "global_accuracy": r["global_accuracy"],
            }
            for r in global_results
        ],
        "final_global_loss": final["global_loss"],
        "final_global_accuracy": final["global_accuracy"],
        "client_summaries": client_summaries,
        "client_distribution_summary": distribution_summary(datasets),
        "mlflow_run_id": None,
        "history_losses_distributed": [
            [int(r), round(float(v), 6)] for r, v in history.losses_distributed
        ],
        "synthetic_only": True,
        "disclaimer": DISCLAIMER,
    }
    return report
