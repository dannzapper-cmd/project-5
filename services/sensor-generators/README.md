# Sensor Generators

Synthetic biomedical-inspired and robotics telemetry publishers for simulated rehab robot operations.

## Phase 1 Status

**Implemented.** Publishes valid `SensorEventV1` JSON to MQTT topics at a configurable interval.

## Streams

| Signal | MQTT Topic | Unit |
|--------|------------|------|
| EMG | `axon/v1/sensors/emg/{node_id}` | mV |
| ECG-like | `axon/v1/sensors/ecg-like/{node_id}` | mV |
| IMU | `axon/v1/sensors/imu/{node_id}` | g/rad_s |
| SpO2-proxy | `axon/v1/sensors/spo2-proxy/{node_id}` | % |
| Robot state | `axon/v1/robot/state/{robot_id}` | state |

## Scenarios

| Scenario | Effect |
|----------|--------|
| `normal_session` | Baseline synthetic rehab session |
| `fatigue_event` | Elevated EMG variability, reduced motion quality |
| `sensor_dropout` | Intermittent low-quality readings |
| `movement_spike` | IMU movement spike |
| `multi_anomaly` | Combined synthetic anomalies |

Scenarios alter stream shape and quality only — no AI decisions in Phase 1.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_HOST` | localhost | Mosquitto host |
| `MQTT_PORT` | 1883 | Mosquitto port |
| `AXON_SCENARIO` | normal_session | Scenario name |
| `AXON_NODE_ID` | rehab-node-01 | Sensor node ID |
| `AXON_ROBOT_ID` | rehab-robot-01 | Robot ID |
| `AXON_PUBLISH_INTERVAL` | 1.0 | Seconds between publish cycles |
| `AXON_SEED` | (none) | Deterministic RNG seed |
| `AXON_TRACE_ID` | session-synthetic-001 | Trace ID for all events |

## Run Locally

```bash
# With core stack running
MQTT_HOST=localhost python -m axon_generators
```

## Docker

Started automatically via `docker compose --profile core up --build`.

## Evidence to Collect

- Generator log lines showing topic publishes
- MQTT subscribe proof
- Dashboard live updates

## Safety

Synthetic signals only. Not medical data. Not for diagnosis or treatment.
