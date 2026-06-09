#!/usr/bin/env bash
# Phase 9 verification — lightweight default; optional full verify via AXON_PHASE9_FULL_VERIFY=1
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

VERIFY_DIR="/tmp/phase9_verify_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$VERIFY_DIR"
export AXON_PHASE9_VERIFY_DIR="$VERIFY_DIR"

echo "=== Phase 9 Verification (Final Seal) ==="
echo "Temp outputs: $VERIFY_DIR"

BLOCK1_OK=1

echo "--- Block 1: Tracked runtime artifact hygiene ---"
if tracked_phase8="$(git ls-files 'artifacts/phase8/phase8_scenario_*.json')" && [ -n "$tracked_phase8" ]; then
  echo "FAIL: Phase 8 runtime scenario JSON files are tracked:"
  echo "$tracked_phase8" | sed 's/^/  /'
  BLOCK1_OK=0
else
  echo "PASS: no tracked Phase 8 runtime scenario JSON files"
fi

if dirty_snapshots="$(git diff --name-only -- artifacts/observability artifacts/reliability)" && [ -n "$dirty_snapshots" ]; then
  echo "FAIL: committed observability/reliability snapshots are dirty:"
  echo "$dirty_snapshots" | sed 's/^/  /'
  BLOCK1_OK=0
else
  echo "PASS: committed observability/reliability snapshots are clean"
fi

echo "--- Block 1: Python syntax (apps/) ---"
if "$PYTHON" - <<'PY'
import ast
import sys
from pathlib import Path

root = Path("apps")
errors = []
for path in sorted(root.rglob("*.py")):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        errors.append(f"{path}:{exc.lineno}: {exc.msg}")
if errors:
    print("FAIL: Python syntax errors:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
print("PASS: Python syntax")
PY
then
  :
else
  BLOCK1_OK=0
fi

echo "--- Block 1: Unqualified fine-tuning claim scan ---"
if "$PYTHON" - <<'PY'
import re
import sys
from pathlib import Path

QUALIFIERS = re.compile(
    r"not fine-tuning|not neural fine-tuning|is not fine-tuning|no fine-tuning",
    re.I,
)
META = re.compile(r"unqualified fine[- ]tuning|fine[- ]tuning claim scan", re.I)
PATTERN = re.compile(r"fine[- ]tuning", re.I)
SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
SCAN = {".py", ".md", ".html", ".js", ".sh", ".yml", ".toml"}
SKIP_FILES = {Path("scripts/verify_phase9.sh")}
violations = []
for base in [Path("apps"), Path("docs"), Path("scripts"), Path("README.md"), Path("ROADMAP.md")]:
    paths = [base] if base.is_file() else list(base.rglob("*"))
    for path in paths:
        if path in SKIP_FILES:
            continue
        if not path.is_file() or path.suffix.lower() not in SCAN:
            continue
        if any(p in SKIP for p in path.parts):
            continue
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if META.search(line):
                continue
            if PATTERN.search(line) and not QUALIFIERS.search(line):
                violations.append(f"{path}:{idx}: {line.strip()}")
if violations:
    print("FAIL: unqualified fine-tuning claims:")
    for v in violations:
        print(f"  {v}")
    sys.exit(1)
print("PASS: fine-tuning claims qualified or absent")
PY
then
  :
else
  BLOCK1_OK=0
fi

echo "--- Block 1: Phase/version consistency ---"
if "$PYTHON" - <<'PY'
import re
import sys
from pathlib import Path

import tomllib

from apps.api.app.core.config import Settings

settings = Settings()
pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
version = pyproject["project"]["version"]
errors = []
if version != settings.axon_version:
    errors.append(f"pyproject version {version} != config {settings.axon_version}")
readme = Path("README.md").read_text(encoding="utf-8")
if "feat/phase-9-pass1-credibility-hardening" in readme:
    errors.append("README still references stale pass1 branch name")
if not re.search(r"Phase 9", readme):
    errors.append("README missing Phase 9 acknowledgement")
if errors:
    print("FAIL: phase/version consistency:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
print(f"PASS: version={version}, axon_phase={settings.axon_phase}")
PY
then
  :
else
  BLOCK1_OK=0
fi

echo "--- Block 1: Evidence index sanity ---"
if "$PYTHON" - <<'PY'
import sys
from pathlib import Path

from apps.api.app.mission.evidence_index import build_evidence_index
from apps.api.app.mission.paths import ROOT

index = build_evidence_index(force_refresh=True)
errors = []
for item in index["items"]:
    path = ROOT / item["path"]
    if not path.exists():
        if item.get("exists"):
            errors.append(f"{item['path']}: exists=True but file missing")
        if item.get("status") == "available":
            errors.append(f"{item['path']}: status=available but file missing")
    else:
        if not item.get("exists"):
            errors.append(f"{item['path']}: file present but exists=False")
        if item.get("status") not in ("available", "unparsed"):
            errors.append(f"{item['path']}: on-disk file has status={item.get('status')}")
if errors:
    print("FAIL: evidence index integrity:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
print(
    f"PASS: evidence index ({index['summary']['total']} items, "
    f"{index['summary']['not_generated']} not_generated)"
)
PY
then
  :
else
  BLOCK1_OK=0
fi

echo "--- Block 1: Safety/medical claim scan ---"
if "$PYTHON" scripts/scan_claims.py; then
  :
else
  BLOCK1_OK=0
fi

echo "--- Block 1: Claim scan unit tests ---"
if "$PYTEST" tests/phase9/test_scan_claims.py -q; then
  :
else
  BLOCK1_OK=0
fi

if [ "$BLOCK1_OK" -ne 1 ]; then
  echo "=== Phase 9 Block 1 FAILED ==="
  exit 1
fi

echo "--- Block 2: Docker Compose config checks ---"
if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
  docker compose --profile learning config >/dev/null
  docker compose --profile obs config >/dev/null
  docker compose --profile ros2 config >/dev/null
  docker compose --profile ros2-nav-slam config >/dev/null
  echo "PASS: Docker Compose profiles validate"
else
  echo "Docker CLI not found — Block 2 NOT RUN"
  echo "=== Phase 9 verification complete (Block 1 only) ==="
  exit 0
fi

if [ "${AXON_PHASE9_FULL_VERIFY:-}" = "1" ]; then
  echo "--- Block 3: Full verification (AXON_PHASE9_FULL_VERIFY=1) ---"
  bash scripts/verify_phase4.sh
  bash scripts/verify_phase6a.sh
  bash scripts/verify_phase6b.sh
  bash scripts/verify_phase8.sh
  "$PYTEST" tests/phase8/ tests/phase4/test_mlops.py -q
  echo "PASS: optional full verification"
fi

echo "=== Phase 9 verification complete ==="
