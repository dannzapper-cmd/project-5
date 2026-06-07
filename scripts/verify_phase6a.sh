#!/usr/bin/env bash
# Phase 6A verification — federated learning simulation.
# Lightweight: lint + FL tests (tiny fixtures) + smoke run + compose profile
# checks + safety grep + ROS2 freeze check. No long training.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${VENV:-.venv}"
PYTHON="${VENV}/bin/python"
PYTEST="${VENV}/bin/pytest"
RUFF="${VENV}/bin/ruff"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
  PYTEST="pytest"
  RUFF="ruff"
fi

echo "=== Phase 6A Verification ==="

echo "--- Lint (FL module + API + tests) ---"
if command -v "$RUFF" >/dev/null 2>&1 || [ -x "$RUFF" ]; then
  "$RUFF" check apps/learning apps/api/app/learning apps/api/app/routes/learning.py \
    apps/api/app/schemas/learning.py scripts/run_federated_learning.py tests/phase6a
  echo "PASS: lint"
else
  echo "SKIP: ruff not installed"
fi

echo "--- Phase 6A tests (tiny fixtures) ---"
"$PYTEST" tests/phase6a/ -q
echo "PASS: phase6a tests"

echo "--- FL smoke run (2 clients, 1 round) ---"
"$PYTHON" scripts/run_federated_learning.py --smoke --no-mlflow >/dev/null
test -f artifacts/learning/federated/federated_report.json
echo "PASS: smoke run + report"

echo "--- Report schema sanity ---"
"$PYTHON" - <<'PY'
import json
r = json.load(open("artifacts/learning/federated/federated_report.json"))
required = {
    "experiment_id", "timestamp_utc", "seed", "num_clients", "num_rounds",
    "local_epochs", "model_type", "global_results", "client_summaries",
    "mlflow_run_id", "disclaimer",
}
missing = required - set(r)
assert not missing, f"missing report fields: {missing}"
assert r["model_type"] == "AxonFLModelV1"
assert "No real patient data" in r["disclaimer"]
print("PASS: report schema")
PY

if command -v docker >/dev/null 2>&1; then
  echo "--- Docker compose core config ---"
  docker compose --profile core config >/dev/null
  echo "PASS: core compose config"

  echo "--- Docker compose learning config ---"
  docker compose --profile learning config >/dev/null
  echo "PASS: learning compose config"

  echo "--- FL deps absent from core profile ---"
  if docker compose --profile core config 2>/dev/null | grep -qiE 'fl-runner|flwr'; then
    echo "FAIL: FL service/dep found in core profile"
    exit 1
  fi
  echo "PASS: FL not in core profile"
else
  echo "SKIP: docker not available — run 'docker compose --profile core|learning config' locally"
fi

echo "--- Safety banned terms grep ---"
BANNED_TERMS=(
  "medical-grade"
  "medical grade"
  "clinical decision"
  "patient outcome"
  "treatment recommendation"
  "hospital deployment"
)
PHASE6A_PATHS=(
  apps/learning
  apps/api/app/learning
  apps/api/app/routes/learning.py
  apps/api/app/schemas/learning.py
  scripts/run_federated_learning.py
  tests/phase6a
)
for term in "${BANNED_TERMS[@]}"; do
  if grep -ril "$term" "${PHASE6A_PATHS[@]}" 2>/dev/null | grep -q .; then
    echo "FAIL: Banned term '$term' found in Phase 6A files."
    exit 1
  fi
done
echo "PASS: no banned safety terms"

echo "--- ROS2/Nav2/SLAM freeze check (vs main) ---"
if git rev-parse --verify main >/dev/null 2>&1; then
  if git diff --name-only main...HEAD -- ros2_ws/ robotics/ services/ros2-bridge/ \
      services/ros2-nav-slam-minilab/ 2>/dev/null | grep -q .; then
    echo "FAIL: ROS2/Nav2/SLAM files changed in this branch"
    exit 1
  fi
  echo "PASS: ROS2/Nav2/SLAM untouched"
else
  echo "SKIP: main ref not available"
fi

echo "=== Phase 6A verification complete ==="
