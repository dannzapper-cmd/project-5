# Edge Inference Service

## Purpose

Run ONNX Runtime edge inference on buffered sensor events for anomaly detection and classification.

## Future Phase

Phase 2 — Edge AI Core

## Expected Inputs

- Redis Streams sensor events
- ONNX model artifacts (versioned)
- Inference configuration (batch size, thresholds)

## Expected Outputs

- `ModelScoreEventV1` events to Redis Streams
- Latency metrics for Evidence Center

## Evidence to Collect

- ONNX Runtime inference proof
- Model latency benchmark report
- Model card linkage

## Current Phase 0 Status

**Placeholder only.** No ONNX models or inference runtime implemented.
