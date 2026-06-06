#!/usr/bin/env python3
"""Regenerate replay scenario JSONL files with deterministic SensorEventV1 events."""

from __future__ import annotations

import json
from pathlib import Path

from axon_generators.config import GeneratorConfig
from axon_generators.generator import generate_event_batch
from axon_generators.scenarios import SCENARIOS

REPLAY_DIR = Path(__file__).resolve().parent / "scenarios"
EVENTS_PER_FILE = 25


def generate_file(scenario: str, seed: int) -> None:
    config = GeneratorConfig(
        axon_scenario=scenario,
        axon_trace_id=f"replay-{scenario}",
        axon_source="replay-generator",
        axon_seed=seed,
    )
    path = REPLAY_DIR / f"{scenario}.jsonl"
    lines: list[str] = []
    for tick in range(EVENTS_PER_FILE):
        batch = generate_event_batch(
            config,
            tick,
            mode="replay",
            scenario_name=scenario,
            seed=seed + tick,
        )
        for topic, event in batch:
            record = {"topic": topic, "event": event.model_dump(mode="json")}
            lines.append(json.dumps(record))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} lines -> {path}")


def main() -> None:
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    for idx, scenario in enumerate(SCENARIOS):
        generate_file(scenario, seed=1000 + idx * 100)


if __name__ == "__main__":
    main()
