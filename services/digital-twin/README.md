# AXON Digital Twin (Phase 5)

Implemented in Phase 5 — not a placeholder.

- **Schema:** `DigitalTwinStateV1` in `apps/api/app/schemas/twin.py`
- **Service:** `apps/api/app/twin/service.py` (consumes existing Redis/agent pipeline)
- **WebSocket:** `/ws/v1/twin`
- **REST:** `GET /api/v1/twin/state`, `POST /api/v1/twin/command`
- **Dashboard:** SVG live mirror in `apps/dashboard/`

See `docs/evidence/phase-5-digital-twin-ros2.md` for QA checklist.
