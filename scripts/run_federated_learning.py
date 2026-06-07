#!/usr/bin/env python3
"""Run the Phase 6A federated learning simulation (Flower + FedAvg).

Synthetic federated learning simulation. No real patient data. No medical claims.

Examples:
    python scripts/run_federated_learning.py                 # default 3-client run
    python scripts/run_federated_learning.py --num-clients 5 --num-rounds 5
    python scripts/run_federated_learning.py --smoke         # tiny CI-friendly run
"""

from __future__ import annotations

import argparse
import json
import sys

from apps.learning.federated.config import (
    CONVERGENCE_CSV_PATH,
    DEFAULT_LEARNING_RATE,
    DEFAULT_LOCAL_EPOCHS,
    DEFAULT_NUM_ROUNDS,
    DEFAULT_SEED,
    LATEST_REPORT_PATH,
)
from apps.learning.federated.runner import run_and_persist


def main() -> None:
    parser = argparse.ArgumentParser(description="AXON Phase 6A federated learning")
    parser.add_argument("--num-clients", type=int, default=3)
    parser.add_argument("--num-rounds", type=int, default=DEFAULT_NUM_ROUNDS)
    parser.add_argument("--local-epochs", type=int, default=DEFAULT_LOCAL_EPOCHS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--dataset-size", type=int, default=None)
    parser.add_argument("--no-mlflow", action="store_true", help="Skip MLflow logging")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Tiny CI-friendly run (2 clients, 1 round, 1 epoch, 50 samples)",
    )
    args = parser.parse_args()

    if args.smoke:
        args.num_clients = 2
        args.num_rounds = 1
        args.local_epochs = 1
        args.dataset_size = 50

    report = run_and_persist(
        num_clients=args.num_clients,
        num_rounds=args.num_rounds,
        local_epochs=args.local_epochs,
        seed=args.seed,
        learning_rate=args.learning_rate,
        dataset_size=args.dataset_size,
        log_mlflow=not args.no_mlflow,
    )

    print(
        json.dumps(
            {
                "experiment_id": report["experiment_id"],
                "num_clients": report["num_clients"],
                "num_rounds": report["num_rounds"],
                "final_global_loss": report["final_global_loss"],
                "final_global_accuracy": report["final_global_accuracy"],
                "mlflow_run_id": report["mlflow_run_id"],
                "report_path": str(LATEST_REPORT_PATH),
                "convergence_csv": str(CONVERGENCE_CSV_PATH),
                "disclaimer": report["disclaimer"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
