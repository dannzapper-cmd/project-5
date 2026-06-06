# ADR-003: ONNX Runtime over Direct PyTorch Inference for Edge-Like Deployment

- **Status:** Proposed
- **Date:** 2026-06-05

## Context

AXON targets edge-like inference for small models (EMG anomaly, IMU classifier, etc.) with measurable latency evidence. Training may use PyTorch or similar, but deployment should align with edge constraints and optional hardware paths (Jetson, TFLite Micro).

## Decision to Evaluate

Use **ONNX Runtime** for inference serving; keep training frameworks separate from the hot inference path.

## Options to Compare

| Option | Pros | Cons |
|--------|------|------|
| ONNX Runtime | Portable, edge-friendly, benchmarkable | Export step required |
| Direct PyTorch inference | Training/inference unity | Heavier runtime on edge |
| TensorFlow Lite / Edge Impulse | TinyML hardware path | Parallel tooling complexity |

## Evidence Needed

- Inference latency benchmarks per model (Phase 2)
- Model export reproducibility (Phase 4)
- Optional Jetson/TFLite Micro comparison (Phase 8)

## Future Phase

Phase 2 — Edge AI Core
