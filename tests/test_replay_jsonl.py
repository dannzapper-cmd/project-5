"""Validate pre-generated replay JSONL scenario files."""

import json
from pathlib import Path

import pytest
from apps.api.app.schemas.events import SensorEventV1

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "replay" / "scenarios"
SCENARIO_FILES = [
    "normal_session.jsonl",
    "fatigue_event.jsonl",
    "sensor_dropout.jsonl",
    "movement_spike.jsonl",
    "multi_anomaly.jsonl",
]


@pytest.mark.parametrize("filename", SCENARIO_FILES)
def test_replay_jsonl_contains_valid_events(filename: str) -> None:
    path = SCENARIO_DIR / filename
    assert path.exists(), f"Missing replay file: {path}. Run make replay-generate"
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 20, f"{filename} must contain at least 20 events"
    for line in lines:
        record = json.loads(line)
        assert "topic" in record and "event" in record
        event = SensorEventV1.model_validate(record["event"])
        assert event.schema_version == "v1"
