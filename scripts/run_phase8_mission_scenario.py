#!/usr/bin/env python3
"""Run a Phase 8 mission scenario and write evidence artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.mission.constants import SCENARIO_NAMES  # noqa: E402
from apps.api.app.mission.scenarios import run_scenario, validate_artifact_payload  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 8 mission scenario")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=list(SCENARIO_NAMES),
        help="Scenario name",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Optionally enrich from live mission status if API modules loaded",
    )
    args = parser.parse_args()

    try:
        result = run_scenario(args.scenario, enrich_from_api=args.enrich)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for path in result["artifact_paths"].values():
        path_obj = Path(path)
        if path_obj.suffix != ".json":
            continue
        payload = json.loads(path_obj.read_text(encoding="utf-8"))
        try:
            validate_artifact_payload(payload, label=path)
        except ValueError as exc:
            print(f"ERROR: post-generation validation failed for {path}: {exc}", file=sys.stderr)
            return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
