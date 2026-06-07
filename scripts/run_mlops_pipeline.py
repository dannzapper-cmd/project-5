#!/usr/bin/env python3
"""Run Phase 4 MLOps pipeline (dataset + eval + registry)."""

from __future__ import annotations

import argparse
import os
import sys

from apps.mlops.backend import get_mlops_backend
from apps.mlops.config import MLOPS_ARTIFACTS
from apps.mlops.evaluate import run_full_pipeline
from apps.mlops.registry import ensure_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="AXON Phase 4 MLOps pipeline")
    parser.add_argument("--smoke", action="store_true", help="Tiny dataset for CI/smoke")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.smoke:
        os.environ["AXON_MLOPS_SMOKE"] = "true"

    ensure_registry()
    run_dir = MLOPS_ARTIFACTS / "runs" / f"run-{args.seed}"
    backend = get_mlops_backend(str(run_dir))
    backend.log_params({"seed": args.seed, "smoke": args.smoke})

    reports = run_full_pipeline(smoke=args.smoke, seed=args.seed)
    for sig, report in reports.items():
        backend.log_metrics(
            {
                f"{sig}_v1_accuracy": report["v1"]["accuracy"],
                f"{sig}_v2_accuracy": report["v2_candidate"]["accuracy"],
            }
        )
    backend.end_run()
    print(f"Phase 4 pipeline complete. Evals: {list(reports.keys())}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
