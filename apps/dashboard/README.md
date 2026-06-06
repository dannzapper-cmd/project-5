# AXON Dashboard

Live operations dashboard for simulated rehabilitation robot operations.

## Phase 1 Status

**Live telemetry dashboard** served as static HTML/JS on port **3000**.

### Features

- Connection status (API, WebSocket sensors, WebSocket robot state)
- Live cards for EMG, ECG-like, IMU, SpO2-proxy, robot_state
- Sparkline per signal
- Latest value, quality, timestamp
- Event counter and last 20 events table
- Scenario and mode labels from event metadata
- Disabled placeholders for Phase 2+ panels

### WebSocket Configuration

Browser connects to **host-accessible** URLs (not Docker internal names):

- Default: `ws://localhost:8000` (see `config.js`)
- Override via `window.AXON_CONFIG.wsBase` if needed

## URLs

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API health | http://localhost:8000/health |
| Telemetry status | http://localhost:8000/telemetry/status |

## Run

```bash
make compose-core
# Open http://localhost:3000
```

Or serve locally:

```bash
cd apps/dashboard && python -m http.server 3000
```

## Safety Label

Dashboard displays: *Synthetic biomedical-inspired signals only. Not medical data.*

## Future (Phase 2+)

- Model scores, fusion confidence
- Agent traces, HITL UI
- Digital twin (Phase 5)
