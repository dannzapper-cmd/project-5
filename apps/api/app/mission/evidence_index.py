"""Unified internal Evidence Center index (honest file existence checks)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.api.app.mission.constants import EVIDENCE_TTL_S, PHASE
from apps.api.app.mission.paths import (
    DOCS_EVIDENCE,
    FL_ARTIFACTS,
    GENERATE_CMDS,
    MISSION_EVIDENCE_INDEX_ARTIFACT,
    MISSION_STATUS_ARTIFACT,
    MISSION_TIMELINE_ARTIFACT,
    MLOPS_ARTIFACTS,
    MLOPS_DOC_ARTIFACTS,
    OBSERVABILITY_ARTIFACTS,
    PHASE8_DIR,
    RELIABILITY_ARTIFACTS,
    RL_ARTIFACTS,
    ROOT,
)

_evidence_cache: dict[str, Any] | None = None
_evidence_cache_ts: float = 0.0


def _file_mtime_iso(path: Path) -> str | None:
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _safe_json_summary(path: Path) -> tuple[str, str | None]:
    """Return (summary, parse_error)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"JSON artifact at {path.name}", str(exc)
    if isinstance(data, dict):
        keys = ", ".join(sorted(data.keys())[:8])
        extra = "…" if len(data) > 8 else ""
        return f"JSON keys: {keys}{extra}", None
    return f"JSON {type(data).__name__} at {path.name}", None


def _rel_path(path: Path) -> str:
    if path.is_relative_to(ROOT):
        return str(path.relative_to(ROOT))
    return str(path)


def _committed_item(
    *,
    item_id: str,
    category: str,
    title: str,
    path: Path,
    phase_source: str,
) -> dict[str, Any]:
    """Committed docs or on-disk artifacts — missing when absent."""
    exists = path.exists()
    entry: dict[str, Any] = {
        "id": item_id,
        "category": category,
        "title": title,
        "path": _rel_path(path),
        "exists": exists,
        "artifact_kind": "committed",
        "generated_at": _file_mtime_iso(path) if exists else None,
        "phase_source": phase_source,
    }
    if not exists:
        entry["status"] = "missing"
        entry["summary"] = "Artifact not found on disk"
        return entry

    if path.suffix == ".json":
        summary, parse_error = _safe_json_summary(path)
        entry["summary"] = summary
        if parse_error:
            entry["status"] = "unparsed"
            entry["parse_error"] = parse_error
        else:
            entry["status"] = "available"
            mtime = path.stat().st_mtime
            age_s = datetime.now(tz=UTC).timestamp() - mtime
            if age_s > EVIDENCE_TTL_S:
                entry["stale"] = True
        return entry

    entry["status"] = "available"
    entry["summary"] = f"File present ({path.suffix or 'no extension'})"
    mtime = path.stat().st_mtime
    age_s = datetime.now(tz=UTC).timestamp() - mtime
    if age_s > EVIDENCE_TTL_S:
        entry["stale"] = True
    return entry


def _generated_item(
    *,
    item_id: str,
    category: str,
    title: str,
    path: Path,
    phase_source: str,
    generate_cmd: str,
) -> dict[str, Any]:
    """Optional runtime-generated artifacts — not_generated when absent."""
    exists = path.exists()
    entry: dict[str, Any] = {
        "id": item_id,
        "category": category,
        "title": title,
        "path": _rel_path(path),
        "exists": exists,
        "artifact_kind": "generated",
        "generated_at": _file_mtime_iso(path) if exists else None,
        "phase_source": phase_source,
    }
    if not exists:
        entry["status"] = "not_generated"
        entry["generate_cmd"] = generate_cmd
        entry["summary"] = "Artifact not generated locally"
        return entry

    if path.suffix == ".json":
        summary, parse_error = _safe_json_summary(path)
        entry["summary"] = summary
        if parse_error:
            entry["status"] = "unparsed"
            entry["parse_error"] = parse_error
        else:
            entry["status"] = "available"
            mtime = path.stat().st_mtime
            age_s = datetime.now(tz=UTC).timestamp() - mtime
            if age_s > EVIDENCE_TTL_S:
                entry["stale"] = True
        return entry

    entry["status"] = "available"
    entry["summary"] = f"File present ({path.suffix or 'no extension'})"
    mtime = path.stat().st_mtime
    age_s = datetime.now(tz=UTC).timestamp() - mtime
    if age_s > EVIDENCE_TTL_S:
        entry["stale"] = True
    return entry


def _discover_phase_docs() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not DOCS_EVIDENCE.is_dir():
        return items
    for path in sorted(DOCS_EVIDENCE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(DOCS_EVIDENCE)
        phase_tag = rel.parts[0] if rel.parts else "general"
        items.append(
            _committed_item(
                item_id=f"phase_doc_{rel.as_posix().replace('/', '_')}",
                category="phase_evidence",
                title=path.name,
                path=path,
                phase_source=phase_tag,
            )
        )
    return items


def _discover_mission_scenario_artifacts() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not PHASE8_DIR.is_dir():
        return items
    for path in sorted(PHASE8_DIR.glob("phase8_scenario_*.json")):
        items.append(
            _generated_item(
                item_id=f"mission_scenario_{path.stem}",
                category="mission_scenario",
                title=path.name,
                path=path,
                phase_source=PHASE,
                generate_cmd=GENERATE_CMDS["mission_scenario"],
            )
        )
    return items


def build_evidence_index(*, force_refresh: bool = False) -> dict[str, Any]:
    """Scan known artifact paths and return an honest evidence index."""
    global _evidence_cache, _evidence_cache_ts

    import time

    now = time.time()
    if (
        not force_refresh
        and _evidence_cache is not None
        and (now - _evidence_cache_ts) < EVIDENCE_TTL_S
    ):
        return dict(_evidence_cache)

    items: list[dict[str, Any]] = []

    for key, path in FL_ARTIFACTS.items():
        items.append(
            _generated_item(
                item_id=f"fl_{key}",
                category="federated_learning",
                title=path.name,
                path=path,
                phase_source="phase_6a",
                generate_cmd=GENERATE_CMDS["federated_learning"],
            )
        )

    for key, path in RL_ARTIFACTS.items():
        items.append(
            _generated_item(
                item_id=f"rl_{key}",
                category="reinforcement_learning",
                title=path.name,
                path=path,
                phase_source="phase_6b",
                generate_cmd=GENERATE_CMDS["reinforcement_learning"],
            )
        )

    for key, path in MLOPS_ARTIFACTS.items():
        items.append(
            _generated_item(
                item_id=f"mlops_{key}",
                category="mlops",
                title=path.name,
                path=path,
                phase_source="phase_4",
                generate_cmd=GENERATE_CMDS["mlops"],
            )
        )

    for key, path in MLOPS_DOC_ARTIFACTS.items():
        items.append(
            _committed_item(
                item_id=f"mlops_doc_{key}",
                category="mlops",
                title=path.name,
                path=path,
                phase_source="phase_4",
            )
        )

    for key, path in RELIABILITY_ARTIFACTS.items():
        items.append(
            _committed_item(
                item_id=f"reliability_{key}",
                category="reliability",
                title=path.name,
                path=path,
                phase_source="phase_7",
            )
        )

    for key, path in OBSERVABILITY_ARTIFACTS.items():
        items.append(
            _committed_item(
                item_id=f"observability_{key}",
                category="observability",
                title=path.name,
                path=path,
                phase_source="phase_7",
            )
        )

    twin_paths = [
        (ROOT / "artifacts" / "twin", "digital_twin"),
    ]
    for base, category in twin_paths:
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    items.append(
                        _committed_item(
                            item_id=f"{category}_{path.name}",
                            category=category,
                            title=path.name,
                            path=path,
                            phase_source="phase_5",
                        )
                    )

    agent_evidence = DOCS_EVIDENCE / "phase-3-agent-graph.md"
    items.append(
        _committed_item(
            item_id="agents_graph_evidence",
            category="agents",
            title=agent_evidence.name,
            path=agent_evidence,
            phase_source="phase_3",
        )
    )
    safety_evidence = DOCS_EVIDENCE / "phase-3-agents-safety.md"
    items.append(
        _committed_item(
            item_id="safety_hitl_evidence",
            category="safety_hitl",
            title=safety_evidence.name,
            path=safety_evidence,
            phase_source="phase_3",
        )
    )

    ros2_doc = DOCS_EVIDENCE / "phase-5-5-nav2-slam-minilab.md"
    items.append(
        _committed_item(
            item_id="ros2_nav_slam_doc",
            category="ros2",
            title=ros2_doc.name,
            path=ros2_doc,
            phase_source="phase_5",
        )
    )
    items.append(
        _committed_item(
            item_id="nav_slam_doc",
            category="nav_slam",
            title=ros2_doc.name,
            path=ros2_doc,
            phase_source="phase_5_5",
        )
    )

    items.extend(_discover_phase_docs())
    items.extend(_discover_mission_scenario_artifacts())

    for core_artifact in (
        MISSION_STATUS_ARTIFACT,
        MISSION_EVIDENCE_INDEX_ARTIFACT,
        MISSION_TIMELINE_ARTIFACT,
    ):
        items.append(
            _generated_item(
                item_id=f"mission_{core_artifact.stem}",
                category="mission_scenario",
                title=core_artifact.name,
                path=core_artifact,
                phase_source=PHASE,
                generate_cmd=GENERATE_CMDS["mission_scenario"],
            )
        )

    categories = sorted({i["category"] for i in items})
    available = sum(1 for i in items if i["status"] == "available")
    missing = sum(1 for i in items if i["status"] == "missing")
    not_generated = sum(1 for i in items if i["status"] == "not_generated")

    payload = {
        "phase": PHASE,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "categories": categories,
        "items": items,
        "summary": {
            "total": len(items),
            "available": available,
            "missing": missing,
            "not_generated": not_generated,
            "unparsed": sum(1 for i in items if i["status"] == "unparsed"),
        },
        "synthetic_data_only": True,
        "no_medical_claims": True,
    }

    _evidence_cache = payload
    _evidence_cache_ts = now
    return dict(payload)
