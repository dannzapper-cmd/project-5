# ADR-005: Local-First MLOps with Optional MLflow

## Status

Accepted

## Context

Phase 4 requires experiment tracking and artifact storage for the MLOps loop. Cloud tracking (W&B, remote MLflow) adds network dependency and account overhead unsuitable for the local-first portfolio demo.

## Decision

- **Default backend:** `LocalMLOpsBackend` writes `params.json` and `metrics.json` under `artifacts/mlops/runs/`.
- **Optional backend:** Set `AXON_MLOPS_BACKEND=mlflow` with MLflow service under Docker Compose `learning` profile only.
- Core profile never imports or requires MLflow at startup.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Always-on MLflow | Bloats core RAM; hard dependency for demo |
| W&B cloud | Requires internet and external account |
| DVC | Out of scope; adds sync complexity |

## Consequences

- Evidence is available without any external service.
- MLflow adds visual tracking for portfolio demos when learning profile is started.
- CI uses smoke mode with local backend only.
