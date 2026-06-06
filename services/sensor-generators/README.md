# Sensor Generators

## Purpose

Produce synthetic biomedical-inspired and robotics telemetry streams for simulated rehab robot operations.

## Future Phase

Phase 1 — Telemetry Spine

## Expected Inputs

- Scenario configuration (session profile, signal rates, noise models)
- MQTT broker connection parameters
- Optional replay seed / trace ID

## Expected Outputs

- MQTT messages on `axon/v1/sensors/*` topics
- Pydantic-valid `SensorEventV1` payloads

## Evidence to Collect

- MQTT topic publish proof
- Sample payload screenshots
- Replay mode demo video (Phase 1+)

## Current Phase 0 Status

**Placeholder only.** No sensor generators or streaming logic implemented.
