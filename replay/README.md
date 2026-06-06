# AXON Replay (Phase 1)

Replay foundation for deterministic telemetry demos.

## Scenario Files

Pre-generated JSONL files in `scenarios/` contain valid `SensorEventV1` events with MQTT topics.

| File | Scenario |
|------|----------|
| `normal_session.jsonl` | Baseline simulated rehab session |
| `fatigue_event.jsonl` | Elevated EMG variability |
| `sensor_dropout.jsonl` | Intermittent low quality |
| `movement_spike.jsonl` | IMU movement spike |
| `multi_anomaly.jsonl` | Combined synthetic anomalies |

## Regenerate Scenarios

```bash
make replay-generate
```

Uses deterministic seeds via `axon_generators` module.

## Publish Replay to MQTT

Requires Mosquitto running (e.g. `make telemetry-up`).

```bash
python replay/replay_publish.py --file replay/scenarios/normal_session.jsonl --speed 0.5
```

Options:

- `--file` — JSONL scenario path (required)
- `--speed` — delay between events in seconds (default 0.5)
- `--mqtt-host` — MQTT broker host (default localhost)
- `--mqtt-port` — MQTT broker port (default 1883)

## Makefile Shortcuts

```bash
make replay-normal
make replay-fatigue
make replay-dropout
make replay-spike
make replay-multi
```

## JSONL Format

Each line:

```json
{"topic": "axon/v1/sensors/emg/rehab-node-01", "event": { ... SensorEventV1 ... }}
```

Invalid lines are logged and skipped during replay.

## Phase 1 Scope

Replay publishes to MQTT only. Full Redis replay consumers are Phase 2+.
