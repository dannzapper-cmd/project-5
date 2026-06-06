# Edge Inference Service

Phase 2 ONNX Runtime edge inference service for AXON.

## Purpose

Consume EMG and IMU sensor events from Redis Streams, run ONNX Runtime CPU inference,
and publish `ModelScoreEventV1` to `axon:v1:stream:model_scores`.

## Runtime Path

```
Redis Streams (sensors:emg, sensors:imu)
  → preprocess → ONNX Runtime inference
  → ModelScoreEventV1 → axon:v1:stream:model_scores
```

The API tails the model score stream and broadcasts to `/ws/v1/model-scores`.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `MODEL_DIR` | `/app/models/onnx` | ONNX model directory |
| `METADATA_DIR` | `/app/models/metadata` | Metadata JSON directory |
| `MODEL_SCORE_STREAM` | `axon:v1:stream:model_scores` | Output stream |
| `INFERENCE_INTERVAL_MS` | `500` | Minimum interval between inference batches |

## Consumer Design

- **XREAD with BLOCK** (not consumer groups) — single consumer, simpler restart semantics
- **last_id = "$" on startup** — only new events from now forward; avoids stale reprocessing on restart
- **INFERENCE_INTERVAL_MS** — rate limiting independent of Redis read speed

## Prerequisites

```bash
make models-generate
docker compose --profile core up --build
```

## Supported Signals

| Signal | Model | Unsupported |
|--------|-------|-------------|
| EMG | emg_anomaly_v0 | — |
| IMU | imu_movement_v0 | — |
| ECG-like | — | Future Phase 2+ |
| SpO2-proxy | — | Future (rule-like placeholder) |

## Safety

Synthetic operational scores only. Not medical data. Not for diagnosis or treatment.
