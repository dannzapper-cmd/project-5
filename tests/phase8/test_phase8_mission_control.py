"""Phase 8 integrated mission control tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from apps.api.app.mission.constants import DEFAULT_SEED, SCENARIO_NAMES, TIMELINE_STAGES
from apps.api.app.mission.scenarios import run_scenario, validate_artifact_payload
from apps.api.main import app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
PHASE8_DIR = ROOT / "artifacts" / "phase8"

BANNED_TERMS = [
    "diagnos",
    "clinical",
    "patient",
    "therapeutic",
    "hospital",
    "treat",
    "prognos",
    "medical advice",
    "health outcome",
    "medical device",
    "clinical trial",
]

ALLOWED_CONTEXTS = re.compile(
    r"no_medical_claims|prohibited_claims_test|prohibited claims|Not Doing|"
    r"Non-goals|Scope guardrails|Safety disclaimer|not for diagnosis|"
    r"Not a medical device|no medical decisions|no real patient",
    re.IGNORECASE,
)

PHASE8_GLOB_PATHS = [
    ROOT / "apps" / "api" / "app" / "mission",
    ROOT / "apps" / "api" / "app" / "routes" / "mission.py",
    ROOT / "scripts" / "run_phase8_mission_scenario.py",
    ROOT / "tests" / "phase8",
    ROOT / "docs" / "phase8_mission_control.md",
    ROOT / "docs" / "adr" / "ADR-013-phase8-integrated-mission-control.md",
]


@pytest.fixture
def client():
    return TestClient(app)


def _phase8_source_files() -> list[Path]:
    files: list[Path] = []
    for base in PHASE8_GLOB_PATHS:
        if base.is_file():
            files.append(base)
        elif base.is_dir():
            files.extend(base.rglob("*"))
    return [f for f in files if f.suffix in (".py", ".md", ".html", ".js", ".json", ".sh")]


def test_mission_status_returns_expected_structure(client):
    res = client.get("/mission/status")
    assert res.status_code == 200
    data = res.json()
    assert data["phase"] == "phase_8"
    assert data["synthetic_data_only"] is True
    assert data["no_medical_claims"] is True
    assert "components" in data
    assert "degraded_components" in data
    assert "limitations" in data
    assert isinstance(data["degraded"], bool)
    for key in (
        "synthetic_telemetry",
        "edge_inference",
        "fl_evidence",
        "rl_evidence",
        "observability",
        "reliability",
    ):
        assert key in data["components"]


def test_mission_timeline_returns_ordered_events(client):
    res = client.get("/mission/timeline")
    assert res.status_code == 200
    data = res.json()
    assert data["synthetic_data_only"] is True
    events = data["events"]
    assert isinstance(events, list)
    assert len(events) >= len(TIMELINE_STAGES)
    for event in events:
        for field in (
            "event_id",
            "timestamp",
            "stage",
            "title",
            "summary",
            "source_component",
            "status",
        ):
            assert field in event
        assert event["status"] in {"ok", "warning", "blocked", "skipped", "simulated"}
    stages = [e["stage"] for e in events]
    assert stages == sorted(stages, key=lambda s: TIMELINE_STAGES.index(s))


def test_mission_evidence_honest_existence_flags(client):
    res = client.get("/mission/evidence")
    assert res.status_code == 200
    data = res.json()
    assert data["synthetic_data_only"] is True
    assert "items" in data
    assert "not_generated" in data["summary"]
    for item in data["items"]:
        assert "exists" in item
        assert "status" in item
        path = ROOT / item["path"]
        if item["exists"]:
            assert path.exists(), f"claimed exists but missing: {item['path']}"
            assert item["status"] in ("available", "unparsed")
        else:
            assert item["status"] in ("missing", "not_generated")
            if item["status"] == "not_generated":
                assert "generate_cmd" in item


def test_evidence_index_no_false_available_for_absent_generated():
    from apps.api.app.mission.evidence_index import build_evidence_index

    index = build_evidence_index(force_refresh=True)
    for item in index["items"]:
        path = ROOT / item["path"]
        if not path.exists():
            assert item["status"] != "available", item["path"]
            assert item["exists"] is False


def test_evidence_index_includes_mlops_category():
    from apps.api.app.mission.evidence_index import build_evidence_index

    index = build_evidence_index(force_refresh=True)
    assert "mlops" in index["categories"]
    mlops_items = [i for i in index["items"] if i["category"] == "mlops"]
    assert mlops_items
    for item in mlops_items:
        if item["artifact_kind"] == "generated" and not item["exists"]:
            assert item["status"] == "not_generated"
            assert item["generate_cmd"] == "make mlops-pipeline"


def test_evidence_fl_rl_not_generated_when_absent(monkeypatch, tmp_path):
    from apps.api.app.mission import evidence_index as ei

    missing_fl = tmp_path / "federated_report.json"
    monkeypatch.setattr(
        ei,
        "FL_ARTIFACTS",
        {"federated_report": missing_fl},
    )
    monkeypatch.setattr(ei, "RL_ARTIFACTS", {"rl_report": tmp_path / "rl_report.json"})
    monkeypatch.setattr(ei, "_evidence_cache", None)
    monkeypatch.setattr(ei, "_evidence_cache_ts", 0.0)

    index = ei.build_evidence_index(force_refresh=True)
    fl = next(i for i in index["items"] if i["id"] == "fl_federated_report")
    rl = next(i for i in index["items"] if i["id"] == "rl_rl_report")
    assert fl["status"] == "not_generated"
    assert fl["generate_cmd"] == "make learning-fl-run"
    assert rl["status"] == "not_generated"
    assert rl["generate_cmd"] == "make learning-rl-run"


@pytest.mark.parametrize("scenario", SCENARIO_NAMES)
def test_scenario_runner_supports_all_scenarios(scenario, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.PHASE8_DIR",
        tmp_path / "phase8",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_STATUS_ARTIFACT",
        tmp_path / "phase8" / "phase8_mission_status.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_TIMELINE_ARTIFACT",
        tmp_path / "phase8" / "phase8_mission_timeline.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_EVIDENCE_INDEX_ARTIFACT",
        tmp_path / "phase8" / "phase8_mission_evidence_index.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.SCENARIO_SUMMARY_ARTIFACT",
        tmp_path / "phase8" / "phase8_scenario_summary.txt",
    )

    result = run_scenario(scenario)
    assert result["scenario"] == scenario
    assert result["status"] == "completed"
    assert result["seed"] == DEFAULT_SEED
    for path in result["artifact_paths"].values():
        assert Path(path).exists()


def test_scenario_runner_writes_valid_json_artifacts(tmp_path, monkeypatch):
    base = tmp_path / "phase8"
    monkeypatch.setattr("apps.api.app.mission.scenarios.PHASE8_DIR", base)
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_STATUS_ARTIFACT",
        base / "phase8_mission_status.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_TIMELINE_ARTIFACT",
        base / "phase8_mission_timeline.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_EVIDENCE_INDEX_ARTIFACT",
        base / "phase8_mission_evidence_index.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.SCENARIO_SUMMARY_ARTIFACT",
        base / "phase8_scenario_summary.txt",
    )

    run_scenario("normal_operation")
    for path in base.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_artifact_payload(data, label=str(path))


def test_timeline_artifact_schema(tmp_path, monkeypatch):
    base = tmp_path / "phase8"
    monkeypatch.setattr("apps.api.app.mission.scenarios.PHASE8_DIR", base)
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_STATUS_ARTIFACT",
        base / "phase8_mission_status.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_TIMELINE_ARTIFACT",
        base / "phase8_mission_timeline.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_EVIDENCE_INDEX_ARTIFACT",
        base / "phase8_mission_evidence_index.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.SCENARIO_SUMMARY_ARTIFACT",
        base / "phase8_scenario_summary.txt",
    )

    run_scenario("normal_operation")
    timeline = json.loads((base / "phase8_mission_timeline.json").read_text())
    assert "events" in timeline
    assert len(timeline["events"]) >= len(TIMELINE_STAGES)


def test_mission_status_degraded_when_all_optional_offline(client, monkeypatch):
    monkeypatch.setattr(
        "apps.api.app.mission.status.telemetry_state",
        type(
            "T",
            (),
            {
                "mqtt_connected": False,
                "redis_connected": False,
                "model_score_stream_connected": False,
                "model_scores_received": 0,
            },
        )(),
    )
    monkeypatch.setattr(
        "apps.api.app.mission.status.get_twin_service_status",
        lambda: {"running": False, "broadcast_hz": 0},
    )
    monkeypatch.setattr("apps.api.app.mission.status.get_latest_twin_state", lambda: None)
    monkeypatch.setattr(
        "apps.api.app.mission.status.get_nav_slam_status",
        lambda: {"bridge_status": "offline", "nav_status": "offline", "slam_status": "offline"},
    )
    monkeypatch.setattr(
        "apps.api.app.mission.status.get_safety_status",
        lambda: {},
    )
    monkeypatch.setattr("apps.api.app.mission.status.get_current_decision", lambda: None)
    monkeypatch.setattr(
        "apps.api.app.mission.status._service_readiness_summary",
        lambda: {"status": "unknown", "components": {}},
    )
    monkeypatch.setattr(
        "apps.api.app.mission.status.build_evidence_index",
        lambda **_: {
            "summary": {
                "available": 0,
                "total": 1,
                "missing": 1,
                "not_generated": 0,
                "unparsed": 0,
            },
            "items": [],
        },
    )
    monkeypatch.setattr("apps.api.app.mission.status._load_latest_scenario_meta", lambda: {})
    monkeypatch.setattr("apps.api.app.mission.status._status_cache", None)
    monkeypatch.setattr("apps.api.app.mission.status._status_cache_ts", 0.0)

    res = client.get("/mission/status")
    assert res.status_code == 200
    data = res.json()
    assert data["degraded"] is True
    assert data["degraded_components"]
    assert data["limitations"]


def test_unknown_scenario_returns_400(client):
    res = client.post("/mission/scenarios/run", json={"scenario": "not_a_scenario"})
    assert res.status_code == 400


def test_prohibited_medical_claims_scan():
    violations: list[str] = []
    for path in _phase8_source_files():
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ALLOWED_CONTEXTS.search(text):
            continue
        for term in BANNED_TERMS:
            if re.search(re.escape(term), text, re.IGNORECASE):
                violations.append(f"{path}: {term}")
    assert not violations, "Banned terms found: " + "; ".join(violations)


def test_scenario_run_non_persisted_on_readonly(tmp_path, monkeypatch):
    base = tmp_path / "phase8"
    monkeypatch.setattr("apps.api.app.mission.scenarios.PHASE8_DIR", base)
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_STATUS_ARTIFACT",
        base / "phase8_mission_status.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_TIMELINE_ARTIFACT",
        base / "phase8_mission_timeline.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.MISSION_EVIDENCE_INDEX_ARTIFACT",
        base / "phase8_mission_evidence_index.json",
    )
    monkeypatch.setattr(
        "apps.api.app.mission.scenarios.SCENARIO_SUMMARY_ARTIFACT",
        base / "phase8_scenario_summary.txt",
    )

    def _raise_readonly(self, *args, **kwargs):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(Path, "write_text", _raise_readonly)

    result = run_scenario("normal_operation")
    assert result["status"] == "completed"
    assert result["persisted"] is False
    assert result["persistence_note"] == "artifact path read-only in this profile"
    assert result["artifact_paths"] == {}


def test_dashboard_mission_control_fallback_present():
    html = (ROOT / "apps" / "dashboard" / "index.html").read_text()
    js = (ROOT / "apps" / "dashboard" / "app.js").read_text()
    assert "mission-control-panel" in html
    assert "mission-api-unreachable" in html
    assert "pollMissionControl" in js
    assert "Mission API unavailable" in html
