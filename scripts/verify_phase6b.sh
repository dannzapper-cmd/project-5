#!/usr/bin/env bash
# Phase 6B verification — RL micro-module.
# Lightweight: lint + RL tests (CI mode, tiny timesteps) + smoke run + schema
# check + compose profile checks + dependency-isolation grep + safety grep +
# ROS2 freeze check + Phase 6A protection. No long training.
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

echo "=== Phase 6B Verification (RL micro-module) ==="

echo "--- Lint (RL module + API + tests) ---"
if command -v "$RUFF" >/dev/null 2>&1 || [ -x "$RUFF" ]; then
  "$RUFF" check apps/learning/rl apps/api/app/learning/rl_service.py \
    apps/api/app/routes/rl.py apps/api/app/schemas/rl.py \
    scripts/run_rl_micro_module.py tests/phase6b
  echo "PASS: lint"
else
  echo "SKIP: ruff not installed"
fi

echo "--- Phase 6B tests (CI mode, tiny timesteps) ---"
RL_CI_MODE=true "$PYTEST" tests/phase6b/ -q
echo "PASS: phase6b tests"

echo "--- RL smoke run (CI mode, 500 timesteps) ---"
"$PYTHON" scripts/run_rl_micro_module.py --ci --no-mlflow >/dev/null
test -f artifacts/learning/rl/rl_report.json
echo "PASS: smoke run + report"

echo "--- Report schema sanity ---"
"$PYTHON" - <<'PY'
import json
r = json.load(open("artifacts/learning/rl/rl_report.json"))
required = {
    "experiment_id", "timestamp_utc", "seed", "env_name", "algorithm",
    "total_timesteps_or_episodes", "observation_dim", "action_count",
    "reward_version", "baseline_reward", "trained_policy_reward", "mean_reward",
    "unsafe_action_rate", "hitl_suggestion_rate", "mlflow_run_id", "disclaimer",
}
missing = required - set(r)
assert not missing, f"missing report fields: {missing}"
assert r["env_name"] == "AxonTriageEnvV1"
assert r["reward_version"] == "REWARD_V1"
assert r["disclaimer"] == (
    "Synthetic RL operational policy. No real patient data. No medical decisions. "
    "Human review required for high-risk actions."
)
print("PASS: report schema")
PY

echo "--- Dependency isolation: gymnasium/SB3 NOT in core deps ---"
if grep -qiE 'gymnasium|stable.baselines3|stable_baselines3' requirements.txt 2>/dev/null; then
  echo "FAIL: RL dep found in requirements.txt"
  exit 1
fi
CORE_DEPS="$("$PYTHON" - <<'PY'
import tomllib
data = tomllib.load(open("pyproject.toml", "rb"))
print("\n".join(data["project"]["dependencies"]))
PY
)"
if echo "$CORE_DEPS" | grep -qiE 'gymnasium|stable.baselines3|torch'; then
  echo "FAIL: RL/learning dep leaked into core [project.dependencies]"
  exit 1
fi
echo "PASS: RL deps isolated from core"

echo "--- FastAPI import isolation (no gymnasium/SB3/torch) ---"
"$PYTHON" - <<'PY'
import sys
sys.modules["stable_baselines3"] = None
sys.modules["gymnasium"] = None
sys.modules["torch"] = None
from apps.api.main import app  # noqa: F401
print("PASS: FastAPI imports without gymnasium/SB3/torch")
PY

if command -v docker >/dev/null 2>&1; then
  echo "--- Docker compose core config ---"
  docker compose --profile core config >/dev/null
  echo "PASS: core compose config"

  echo "--- Docker compose learning config (fl-runner + rl-runner) ---"
  docker compose --profile learning config >/dev/null
  echo "PASS: learning compose config"

  echo "--- RL/FL deps absent from core profile ---"
  if docker compose --profile core config 2>/dev/null \
      | grep -qiE 'rl-runner|gymnasium|stable.baselines3|flwr'; then
    echo "FAIL: RL/FL service/dep found in core profile"
    exit 1
  fi
  echo "PASS: RL/FL not in core profile"

  echo "--- rl-runner present in learning profile ---"
  if ! docker compose --profile learning config 2>/dev/null | grep -q 'rl-runner'; then
    echo "FAIL: rl-runner missing from learning profile"
    exit 1
  fi
  echo "PASS: rl-runner present (coexists with fl-runner)"
else
  echo "SKIP: docker not available — run compose config checks locally"
fi

echo "--- Safety banned terms grep (positive-claim phrases) ---"
BANNED_TERMS=(
  "medical-grade"
  "medical grade"
  "clinical decision"
  "patient outcome"
  "treatment recommendation"
  "hospital deployment"
  "real robotic control"
)
# NOTE: tests/phase6b is intentionally excluded — test_rl_safety.py stores the
# banned phrases as data for its own (source-only) assertions.
PHASE6B_PATHS=(
  apps/learning/rl
  apps/api/app/learning/rl_service.py
  apps/api/app/routes/rl.py
  apps/api/app/schemas/rl.py
  scripts/run_rl_micro_module.py
)
for term in "${BANNED_TERMS[@]}"; do
  if grep -ril "$term" "${PHASE6B_PATHS[@]}" 2>/dev/null | grep -q .; then
    echo "FAIL: Banned term '$term' found in Phase 6B files."
    exit 1
  fi
done
echo "PASS: no banned safety terms"

echo "--- Disclaimer exact text present (dashboard + schema) ---"
DISCLAIMER="Synthetic RL operational policy. No real patient data. No medical decisions. Human review required for high-risk actions."
MATCHES=$(grep -rl "Synthetic RL operational policy" apps/ 2>/dev/null | wc -l)
if [ "$MATCHES" -lt 2 ]; then
  echo "FAIL: disclaimer prefix found in fewer than 2 source files"
  exit 1
fi
grep -q "$DISCLAIMER" apps/dashboard/index.html
grep -q "$DISCLAIMER" apps/api/app/schemas/rl.py
echo "PASS: exact disclaimer in dashboard + schema"

echo "--- Phase 6A FL protection (artifacts paths do not collide) ---"
if grep -rq "federated_report" apps/learning/rl/ 2>/dev/null; then
  echo "FAIL: RL module references federated_report (artifact collision risk)"
  exit 1
fi
if grep -rq "rl_report" apps/learning/federated/ 2>/dev/null; then
  echo "FAIL: federated module references rl_report (artifact collision risk)"
  exit 1
fi
echo "PASS: FL/RL artifact paths isolated"

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

echo "=== Phase 6B verification complete ==="
