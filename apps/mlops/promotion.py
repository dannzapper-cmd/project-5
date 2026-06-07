"""Manual candidate promotion workflow (dry-run default)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from apps.mlops.config import PROMOTION_REVIEWS_DIR
from apps.mlops.paths import assert_not_protected, get_phase2_model_path
from apps.mlops.registry import load_registry, write_registry_atomic

SAFETY_NOTICE = (
    "Simulated candidate review only. No clinical use. No automatic deployment."
)


def promote_candidate(
    signal_type: str,
    dry_run: bool = True,
    confirm_manual_promotion: bool = False,
    operator_note: str = "",
    registry_path: Path | None = None,
) -> dict:
    """Dry-run or manual promotion review — never overwrites Phase 2 active model."""
    registry = load_registry(registry_path)
    candidate = registry.get("candidate_models", {}).get(signal_type)
    active = registry.get("active_models", {}).get(signal_type)

    if not candidate:
        return {
            "dry_run": dry_run,
            "signal_type": signal_type,
            "candidate_path": "",
            "active_path": active.get("artifact_path", "") if active else "",
            "would_overwrite": False,
            "promotion_status": "no_candidate",
            "safety_notice": SAFETY_NOTICE,
            "review_record_id": "",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": "No candidate model registered",
        }

    candidate_path = candidate["artifact_path"]
    active_path = active["artifact_path"] if active else get_phase2_model_path(signal_type)
    active_path_str = str(active_path) if active_path else ""

    assert_not_protected(candidate_path)

    review_id = str(uuid4())
    timestamp = datetime.now(UTC).isoformat()
    would_overwrite = Path(candidate_path).resolve() == Path(active_path_str).resolve()

    record = {
        "review_record_id": review_id,
        "timestamp": timestamp,
        "signal_type": signal_type,
        "dry_run": dry_run,
        "confirm_manual_promotion": confirm_manual_promotion,
        "candidate_path": candidate_path,
        "active_path": active_path_str,
        "would_overwrite": would_overwrite,
        "operator_note": operator_note,
        "safety_notice": SAFETY_NOTICE,
        "action_taken": "none",
    }

    if dry_run:
        record["action_taken"] = "dry_run_review_only"
        promotion_status = candidate.get("promotion_status", "candidate_not_promoted")
    elif confirm_manual_promotion:
        assert_not_protected(active_path_str)
        backup_dir = Path(candidate_path).parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{signal_type}_candidate_backup_{review_id[:8]}.onnx"
        import shutil

        shutil.copy2(candidate_path, backup_path)
        record["action_taken"] = f"copied_candidate_to_backup:{backup_path}"
        record["backup_path"] = str(backup_path)
        candidate["promotion_status"] = "manual_review_complete"
        candidate["notes"] = operator_note or candidate.get("notes", "")
        registry["candidate_models"][signal_type] = candidate
        registry["last_updated"] = timestamp
        from apps.mlops.config import REGISTRY_PATH

        write_registry_atomic(registry, registry_path or REGISTRY_PATH)
        promotion_status = "manual_review_complete"
    else:
        record["action_taken"] = "rejected_missing_confirm_flag"
        promotion_status = candidate.get("promotion_status", "candidate_not_promoted")

    PROMOTION_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    review_file = PROMOTION_REVIEWS_DIR / f"{review_id}.json"
    review_file.write_text(json.dumps(record, indent=2))

    return {
        "dry_run": dry_run,
        "signal_type": signal_type,
        "candidate_path": candidate_path,
        "active_path": active_path_str,
        "would_overwrite": would_overwrite,
        "promotion_status": promotion_status,
        "safety_notice": SAFETY_NOTICE,
        "review_record_id": review_id,
        "timestamp": timestamp,
    }


def promote_candidate_dry_run(signal_type: str) -> dict:
    return promote_candidate(signal_type, dry_run=True)
