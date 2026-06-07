# Drift and Continual Learning

## Detector

`SlidingWindowDriftDetector` in `apps/mlops/drift.py`:

- Window size: `AXON_DRIFT_WINDOW_SIZE` (default 20)
- Threshold: `AXON_DRIFT_CONFIDENCE_THRESHOLD` (default 0.60)
- Runs as asyncio task inside FastAPI API process
- Reads confidence from `axon:v1:stream:model_scores`

## Events

- Schema: `DriftEventV1` in `apps/api/app/schemas/events.py`
- Redis stream: `axon:v1:stream:drift_events`

## Simulated Drift Trigger

```bash
python scripts/trigger_simulated_drift.py --count 25 --confidence 0.35
```

Requires Redis running (core profile).

## Recommendation Only

When drift is detected, recommendation is `evaluate_candidate_model`. No automatic retraining or model replacement.
