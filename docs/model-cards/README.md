# Model Cards

Model cards document purpose, limitations, and evidence for each AXON edge model.

## Phase 0 Status

No trained models exist. Placeholder cards will be added as models are developed.

## Planned Model Cards

| Model | Phase | Purpose |
|-------|-------|---------|
| EMG anomaly / tiny classifier | 2 | Detect anomalous EMG patterns in synthetic stream |
| ECG-like autoencoder | 2 | Reconstruction-based anomaly signal |
| IMU movement anomaly classifier | 2 | Classify unusual motion during rehab sim |
| SpO2-proxy rules/confidence model | 2 | Rule + confidence hybrid for proxy signal |
| Robot state model | 2 | Robot state deviation detection |

## Template (Future)

Each model card must include:

- Model name and version
- Intended use (simulation only)
- Training data (synthetic sources)
- Metrics and benchmarks
- Limitations and failure modes
- Biomedical disclaimer (no clinical validity)
- Evidence links (MLflow run, latency benchmark)

## Related Documents

- [../data-cards/synthetic-signals-card.md](../data-cards/synthetic-signals-card.md)
- [../evidence/evidence-checklist.md](../evidence/evidence-checklist.md)
