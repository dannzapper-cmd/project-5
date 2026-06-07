#!/usr/bin/env bash
# Phase 1 + Phase 2 + Phase 3 regression test gate
set -euo pipefail
cd "$(dirname "$0")/.."
PYTEST="${PYTEST:-.venv/bin/pytest}"
if [[ ! -x "$PYTEST" ]]; then
  PYTEST="python3 -m pytest"
fi
echo "Running Phase 1/2/3 regression suite..."
$PYTEST tests/test_schemas.py tests/test_topic_router.py tests/test_websocket_format.py \
  tests/test_generators.py tests/test_replay_jsonl.py tests/test_phase2_edge_ai.py \
  tests/test_phase3_agents.py -v --tb=short
