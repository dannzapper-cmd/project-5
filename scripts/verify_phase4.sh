#!/usr/bin/env bash
# Phase 4 verification — smoke mode, no heavy training, <60s target
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${VENV:-.venv}"

export AXON_MLOPS_SMOKE=true
export AXON_SMOKE_DATASET_ROWS=100
export AXON_SMOKE_SCENARIOS=3
export AXON_MLOPS_BACKEND=local

PYTHON="${VENV}/bin/python"
PYTEST="${VENV}/bin/pytest"
RUFF="${VENV}/bin/ruff"

if [ ! -x "$PYTHON" ]; then
  PYTHON="${PYTHON:-python3.12}"
  PYTEST="${PYTEST:-pytest}"
  RUFF="${RUFF:-ruff}"
fi

echo "=== Phase 4 Verification ==="

mkdir -p artifacts/mlops/datasets artifacts/mlops/models artifacts/mlops/evals

echo "--- Lint ---"
if [ -x "$RUFF" ]; then
  "$RUFF" check apps/mlops apps/api/app/mlops apps/api/app/routes/mlops.py scripts/run_mlops_pipeline.py tests/phase4
  echo "PASS: lint"
else
  echo "SKIP: ruff not installed"
fi

echo "--- Phase 1/2/3 regression (exclude phase4) ---"
"$PYTEST" tests/ -q --ignore=tests/phase4/
echo "PASS: regression tests"

echo "--- Phase 4 unit tests ---"
"$PYTEST" tests/phase4/ -q
echo "PASS: phase4 tests"

echo "--- MLOps pipeline smoke ---"
"$PYTHON" scripts/run_mlops_pipeline.py --smoke --seed 42
echo "PASS: pipeline smoke"

echo "--- Docker compose core config ---"
docker compose --profile core config > /dev/null
echo "PASS: core compose config"

echo "--- Docker compose learning config ---"
docker compose --profile learning config > /dev/null
echo "PASS: learning compose config"

echo "--- MLflow absent from core profile ---"
if docker compose --profile core config 2>/dev/null | grep -qi 'mlflow:'; then
  echo "FAIL: mlflow service found in core profile"
  exit 1
fi
echo "PASS: mlflow not in core profile"

echo "--- Safety banned terms grep ---"
BANNED_TERMS=(
  "medical-grade"
  "medical grade"
  "clinical decision"
  "patient outcome"
  "treatment recommendation"
  "hospital deployment"
)
PHASE4_PATHS=(
  apps/mlops
  apps/api/app/mlops
  apps/api/app/routes/mlops.py
  scripts/run_mlops_pipeline.py
  scripts/trigger_simulated_drift.py
  tests/phase4
  docs/evidence/phase-4-mlops.md
  docs/evidence/phase-4-verification.md
  docs/evidence/model-card-emg-v2-candidate.md
  docs/evidence/model-card-imu-v2-candidate.md
  docs/evidence/data-card-synthetic-replay.md
  docs/evidence/drift-and-continual-learning.md
  docs/evidence/candidate-promotion-workflow.md
  docs/adr/ADR-005-phase4-local-first-mlops-mlflow-optional.md
  docs/adr/ADR-006-phase4-manual-candidate-promotion.md
)
for term in "${BANNED_TERMS[@]}"; do
  if grep -ril "$term" "${PHASE4_PATHS[@]}" 2>/dev/null | grep -q .; then
    echo "FAIL: Banned term '$term' found in Phase 4 files."
    exit 1
  fi
done
echo "PASS: no banned safety terms"

echo "=== Phase 4 verification complete ==="
