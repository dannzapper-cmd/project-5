# AXON Dashboard

Live operations dashboard for simulated rehabilitation robot operations.

## Phase 0 Status

Static HTML placeholder (`index.html`) served via nginx in the `core` Docker Compose profile.

No live charts, WebSocket clients, or digital twin rendering yet.

## Future Implementation (Phase 1+)

Planned stack options (to be decided in Phase 1):

- React or Next.js for UI
- WebSocket client for real-time channels
- Three.js or similar for digital twin (Phase 5)

## Future Sections

- Live telemetry panels
- Robot state and session view
- Model scores and fusion confidence
- Agent trace timeline
- Safety / HITL confirmation UI
- Evidence Center integration

## Local Preview

```bash
make compose-core
# Dashboard: http://localhost:8080
```
