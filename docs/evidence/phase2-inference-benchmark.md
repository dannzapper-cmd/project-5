# Phase 2 Inference Benchmark

> Synthetic benchmark only. Not representative of production
> hardware. CPU-only inference on developer machine.
> All signals are simulated data, not medical measurements.

Benchmark conducted on synthetic inputs.
Results are operational performance metrics only,
not clinical accuracy metrics.

- Warmup runs: 20
- Measured runs per model: 200

## Results

### emg_anomaly (v0)

| Metric | Value |
|--------|-------|
| Total runs | 200 |
| p50 latency (ms) | 0.0045 |
| p95 latency (ms) | 0.0167 |
| min latency (ms) | 0.0039 |
| max latency (ms) | 0.0605 |
| mean latency (ms) | 0.0066 |

### imu_movement (v0)

| Metric | Value |
|--------|-------|
| Total runs | 200 |
| p50 latency (ms) | 0.0096 |
| p95 latency (ms) | 0.0148 |
| min latency (ms) | 0.0057 |
| max latency (ms) | 0.0427 |
| mean latency (ms) | 0.0096 |

