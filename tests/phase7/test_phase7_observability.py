"""Phase 7 observability script and logging tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_observability_script_offline_generates_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "observability"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "observability" / "check_phase7_observability.py"),
            "--offline",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1)
    report = output_dir / "phase7b_observability_report.json"
    assert report.is_file()
    data = json.loads(report.read_text())
    assert data["phase"] == "phase7"
    assert "run_id" in data
    assert len(data.get("checks", [])) >= 1

    metrics = output_dir / "metrics_snapshot.txt"
    assert metrics.is_file() and metrics.read_text().strip()

    sample = output_dir / "logging_sample.jsonl"
    assert sample.is_file()
    for line in sample.read_text().splitlines():
        obj = json.loads(line)
        assert obj.get("event")
        assert obj.get("message")


def test_reliability_script_offline_generates_artifacts(tmp_path):
    output_dir = tmp_path / "reliability"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "reliability" / "check_phase7_reliability.py"),
            "--offline",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1)
    for name in (
        "phase7a_reliability_report.json",
        "failure_replay_report.json",
    ):
        path = output_dir / name
        assert path.is_file(), name
        json.loads(path.read_text())
