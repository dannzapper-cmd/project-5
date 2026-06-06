# Contributing to AXON

Thank you for contributing to **AXON — Bio-Robotics Edge Command System**.

## Before You Start

1. Read [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)
2. Read [ROADMAP.md](ROADMAP.md) and identify the current phase
3. Review relevant ADRs in [docs/adr/](docs/adr/)
4. Check [docs/evidence/evidence-checklist.md](docs/evidence/evidence-checklist.md)

## Phase Discipline

- Implement only what the current phase requires.
- Do not claim future-phase capabilities in code, docs, or demos.
- Label placeholders honestly.

## Rules for Human and AI Contributors

| Rule | Rationale |
|------|-----------|
| Respect current phase | Prevents scope creep and fake demos |
| Do not collapse AXON into a chatbot or CRUD app | Preserves intelligent systems identity |
| Do not remove mandatory roadmap phases | Protects portfolio completeness |
| No real patient data | Biomedical safety boundary |
| No medical or clinical claims | Legal and ethical boundary |
| Profile-based execution | Local-first, cost-aware development |
| Evidence-driven development | Every feature produces visible proof |
| Small, testable PRs | Senior-leaning delivery practice |
| Ask before architecture changes | Update ADRs when direction shifts |

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
make test
make dev-check
```

## Code Style

- Python 3.11+
- `pyproject.toml` for dependencies and tool config
- `ruff` for linting
- `pytest` for tests
- Pydantic v2 for event schemas

## Pull Request Checklist

- [ ] Changes align with current roadmap phase
- [ ] Tests pass (`make test`)
- [ ] Dev check passes (`make dev-check`)
- [ ] No false claims about implemented capabilities
- [ ] Safety docs updated if touching biomedical or HITL boundaries
- [ ] Evidence checklist updated if delivering demonstrable output
- [ ] ADR created/updated for significant architecture decisions

## Safety

See [docs/safety/](docs/safety/) before working on signals, decisions, or agent outputs.

Synthetic biomedical-inspired signals only. No diagnosis. No treatment advice.
