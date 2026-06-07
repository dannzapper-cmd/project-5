# Learning Service

## Purpose

MLOps, fine-tuning, continual learning, federated learning (Flower), and RL micro-module training loops.

## Phase

- Phase 4 — MLOps + Fine-tuning + Continual Learning (delivered; see `apps/mlops/`)
- Phase 6A — Federated Learning (Flower + FedAvg) — **delivered**
- Phase 6B — RL — future

## Phase 6A: Federated Learning runner

This service provides the Docker `learning`-profile `fl-runner` (one-shot) image
for the federated learning simulation. The FL logic lives in
`apps/learning/federated/`; the runner image (`services/learning/Dockerfile`)
installs the isolated `requirements-learning.txt` (Flower 1.x + CPU torch +
MLflow) and executes `scripts/run_federated_learning.py`.

```bash
docker compose --profile learning run --build fl-runner   # one federated run
# or locally:
make learning-install && make learning-fl-run
```

Synthetic federated learning simulation. No real patient data. No medical claims.

## Expected Inputs

- Labeled synthetic datasets
- Model registry (MLflow)
- Training configuration and drift triggers

## Expected Outputs

- MLflow runs and model artifacts
- Fine-tuning before/after reports
- Flower convergence metrics
- RL reward curves

## Evidence to Collect

- MLflow run screenshots
- Continual learning drift evidence
- Flower convergence chart
- RL reward curve

## Status

MLflow (Phase 4) and Flower federated learning (Phase 6A) are implemented. RL
(Phase 6B) is not yet implemented.
