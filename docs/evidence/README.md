# Evidence Center

The Evidence Center is AXON's proof-of-capability archive. Every major technology must eventually produce visible evidence.

## Purpose

- Portfolio demonstrations
- Interview narratives
- Regression baselines for performance and safety
- Honest phase completion checkpoints

## Structure

| Artifact Type | Location |
|---------------|----------|
| Checklist | [evidence-checklist.md](evidence-checklist.md) |
| Screenshots / videos | `docs/evidence/artifacts/` (future) |
| Benchmarks | `docs/evidence/benchmarks/` (future) |
| Demo commands | [../runbooks/](../runbooks/) |

## Rules

1. Mark evidence with phase number and date
2. Do not claim evidence for unimplemented features
3. Prefer reproducible commands over one-off screenshots
4. Link evidence to ADRs and model/data cards when relevant

## Phase 0 Evidence

Minimum Phase 0 evidence:

- Repo skeleton (this repository)
- Architecture diagrams in `docs/architecture/`
- `make compose-config` validation
- `GET /health` response
- Dashboard placeholder screenshot

See [evidence-checklist.md](evidence-checklist.md) for the full checklist.
