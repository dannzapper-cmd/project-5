# EMG Anomaly v0 Model Card

## Overview

| Field | Value |
|-------|-------|
| Model name | emg_anomaly |
| Version | v0 |
| Signal type | emg |
| Framework | ONNX Runtime (CPU) |
| Input shape | `[1, 8]` float32 |
| Output | score (0–1), label_idx |

## Labels

- `normal`
- `elevated_activity`

## Purpose

Produces an **anomaly-like operational score** from synthetic EMG signal vectors.
Used for Phase 2 edge inference demonstration only.

## Safety Disclaimer

This model produces synthetic operational scores
derived from simulated signals. It has no clinical
validity, does not diagnose any condition, and must
not be used for any medical decision-making.
Input data is entirely synthetic.

## Limitations

- No training on real data
- Tiny deterministic graph with fixed weights
- Not validated for any biomedical application
