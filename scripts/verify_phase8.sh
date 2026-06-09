#!/usr/bin/env bash
# Phase 8 verification — integrated mission control.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${VENV:-.venv}"
PYTHON="${VENV}/bin/python"
PYTEST="${VENV}/bin/pytest"

if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
  PYTEST="pytest"
fi

# Write runtime artifacts to a temp dir so verification does not dirty the git tree.
PHASE8_TMP="$(mktemp -d)"
export AXON_PHASE8_ARTIFACT_DIR="${PHASE8_TMP}/phase8"
mkdir -p "$AXON_PHASE8_ARTIFACT_DIR"
trap 'rm -rf "$PHASE8_TMP"' EXIT

echo "=== Phase 8 Verification (Integrated Mission Control) ==="
echo "Artifact dir (temp): $AXON_PHASE8_ARTIFACT_DIR"

echo "--- Phase 8 pytest ---"
"$PYTEST" tests/phase8/ -q
echo "PASS: phase8 tests"

echo "--- Scenario runner smoke (normal_operation) ---"
"$PYTHON" scripts/run_phase8_mission_scenario.py --scenario normal_operation >/dev/null
test -f "${AXON_PHASE8_ARTIFACT_DIR}/phase8_mission_status.json"
test -f "${AXON_PHASE8_ARTIFACT_DIR}/phase8_mission_timeline.json"
test -f "${AXON_PHASE8_ARTIFACT_DIR}/phase8_mission_evidence_index.json"
test -f "${AXON_PHASE8_ARTIFACT_DIR}/phase8_scenario_summary.txt"
echo "PASS: scenario runner artifacts"

echo "--- Required artifact fields ---"
"$PYTHON" - <<PY
import json
from pathlib import Path

required = {
    "synthetic_data_only",
    "no_medical_claims",
    "run_id",
    "generated_at",
    "scenario",
    "limitations",
    "seed",
}
artifact_dir = Path("${AXON_PHASE8_ARTIFACT_DIR}")
for path in artifact_dir.glob("*.json"):
    data = json.loads(path.read_text())
    missing = required - set(data)
    assert not missing, f"{path}: missing {missing}"
    assert data["synthetic_data_only"] is True
    assert data["no_medical_claims"] is True
    assert data["seed"] == 42
print("PASS: artifact fields")
PY

echo "--- Banned medical-claim terms (Phase 8 files) ---"
BANNED_TERMS=(
  "diagnos"
  "clinical"
  "patient"
  "therapeutic"
  "hospital"
  "treat"
  "prognos"
  "medical advice"
  "health outcome"
  "medical device"
  "clinical trial"
)
ALLOW_CONTEXT='no_medical_claims|prohibited_claims_test|prohibited claims|Not Doing|Non-goals|Scope guardrails|Safety disclaimer|not for diagnosis|Not a medical device|no medical decisions|no real patient'
PHASE8_PATHS=(
  apps/api/app/mission
  apps/api/app/routes/mission.py
  scripts/run_phase8_mission_scenario.py
  tests/phase8
  docs/phase8_mission_control.md
  docs/adr/ADR-013-phase8-integrated-mission-control.md
)
for term in "${BANNED_TERMS[@]}"; do
  matches=$(grep -ril "$term" "${PHASE8_PATHS[@]}" 2>/dev/null || true)
  if [ -n "$matches" ]; then
    while IFS= read -r file; do
      [ -z "$file" ] && continue
      if grep -iE "$ALLOW_CONTEXT" "$file" >/dev/null 2>&1; then
        continue
      fi
      echo "FAIL: banned term '$term' in $file (outside allowed guardrail context)"
      exit 1
    done <<< "$matches"
  fi
done
echo "PASS: banned term scan"

if command -v docker >/dev/null 2>&1; then
  for profile in core learning ros2 ros2-nav-slam obs; do
    echo "--- Docker compose --profile ${profile} config ---"
    if docker compose --profile "$profile" config >/dev/null 2>&1; then
      echo "PASS: ${profile} compose config"
    else
      echo "SKIPPED: profile ${profile} not present or config failed"
    fi
  done
else
  echo "SKIPPED: docker not available — compose config checks"
fi

echo "=== Phase 8 verification complete ==="
