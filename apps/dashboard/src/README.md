# Dashboard Source (Future)

This directory will hold the Phase 1+ frontend implementation.

## Planned Structure

```
src/
  components/     # Reusable UI components
  hooks/          # WebSocket and API hooks
  pages/          # Dashboard views
  stores/         # Client state management
  types/          # TypeScript types mirroring Pydantic schemas
```

## Contract Alignment

Frontend types must align with:

- `apps/api/app/schemas/events.py`
- `docs/schemas/event-contracts.md`
- `docs/schemas/topic-taxonomy.md` (WebSocket channels)

Do not implement live data binding until Phase 1 telemetry spine is complete.
