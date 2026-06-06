# Model Cards

Model cards document purpose, limitations, and evidence for each AXON edge model.

## Phase 2 Models

| Model | Card | Purpose |
|-------|------|---------|
| emg_anomaly v0 | [emg-anomaly-v0.md](emg-anomaly-v0.md) | Anomaly-like operational score from synthetic EMG |
| imu_movement v0 | [imu-movement-v0.md](imu-movement-v0.md) | Movement-risk-like score from synthetic IMU |

## Future Model Cards

| Model | Phase | Purpose |
|-------|-------|---------|
| ECG-like autoencoder | 2+ | Reconstruction-based anomaly signal |
| SpO2-proxy rules/confidence model | 2+ | Rule + confidence hybrid for proxy signal |
| Robot state model | 2+ | Robot state deviation detection |

## Template

Each model card must include:

- Model name and version
- Intended use (simulation only)
- Metrics and benchmarks
- Limitations and failure modes
- Biomedical disclaimer (no clinical validity)
- Evidence links (latency benchmark)

## Related Documents

- [../data-cards/synthetic-signals-card.md](../data-cards/synthetic-signals-card.md)
- [../evidence/evidence-checklist.md](../evidence/evidence-checklist.md)
