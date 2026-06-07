# Phase 4 — MLOps + Continual Learning

## Overview

Phase 4 adds a lightweight, local-first MLOps loop:

1. Synthetic/replay dataset generation
2. Offline v1 vs v2 candidate evaluation
3. Optional MLflow tracking (learning profile)
4. Local artifact fallback
5. Sliding-window drift detection
6. Manual candidate promotion workflow
7. Dashboard MLOps panel

## Commands

```bash
make install
make models-generate          # Phase 2 active models (required for v1 eval)
make mlops-pipeline           # Smoke pipeline
make verify-phase4            # Full Phase 4 verification
```

With MLflow (learning profile):

```bash
docker compose --profile learning up -d mlflow
AXON_MLOPS_BACKEND=mlflow MLFLOW_TRACKING_URI=http://localhost:5001 make mlops-pipeline
```

## Synthetic Only

All datasets and models use synthetic biomedical-inspired signals. No real patient data. No clinical claims.

## Safety

- Candidate models are never auto-promoted.
- Phase 2 active ONNX paths are protected.
- Drift detection recommends evaluation only; no automatic retraining or deployment.
