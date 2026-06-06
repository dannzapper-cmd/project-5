# Fusion Service

## Purpose

Fuse multi-modal synthetic sensor streams into a unified operational state with confidence scoring.

## Future Phase

Phase 2 — Edge AI Core

## Expected Inputs

- Sensor events from Redis Streams (EMG, ECG-like, IMU, SpO2-proxy, robot state)
- Fusion policy configuration

## Expected Outputs

- Fused state events on `axon:v1:stream:fusion`
- Confidence and missing-data flags

## Evidence to Collect

- Fusion confidence screenshot
- Missing/corrupt data scenario proof

## Current Phase 0 Status

**Placeholder only.** No fusion algorithms implemented.
