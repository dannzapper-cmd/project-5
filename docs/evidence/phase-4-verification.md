# Phase 4 Verification

Run:

```bash
make verify-phase4
```

Checks:

- Ruff lint on Phase 4 modules
- Phase 1/2/3 regression tests
- Phase 4 unit tests (offline)
- MLOps pipeline smoke (`AXON_MLOPS_SMOKE=true`)
- Docker Compose `core` and `learning` config
- MLflow absent from core profile
- Banned safety term grep

Target: complete in under 60 seconds on laptop CPU.
