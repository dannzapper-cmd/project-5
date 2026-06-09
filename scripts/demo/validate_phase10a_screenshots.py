#!/usr/bin/env python3
"""Validate Phase 10A screenshot PNG evidence (stdlib only)."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / "docs/evidence/phase10/demo/screenshots/latest"

EXPECTED = [
    "00_dashboard_overview.png",
    "01_live_telemetry_streams.png",
    "02_edge_inference_and_fusion.png",
    "03_agent_traces_and_hitl.png",
    "04_digital_twin_state_mirror.png",
    "05_evidence_center_or_observability.png",
    "06_failure_or_degraded_mode_if_available.png",
    "07_ros2_nav_slam_compose_status_if_available.png",
]


def analyze_png(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "status": "FAIL", "notes": "missing"}

    data = path.read_bytes()
    size_kb = round(len(data) / 1024, 1)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return {
            "exists": True,
            "valid_png": False,
            "size_kb": size_kb,
            "status": "FAIL",
            "notes": "bad signature",
        }

    width, height = struct.unpack(">II", data[16:24])
    sample = data[100 : min(len(data), 50000)]
    mean = sum(sample) / len(sample) if sample else 0
    var_score = sum((b - mean) ** 2 for b in sample) / len(sample) if sample else 0
    mid = data[len(data) // 3 : len(data) // 3 + 10000] if len(data) > 30000 else sample
    mostly_blank = False
    if mid:
        white = sum(1 for b in mid if b > 250) / len(mid)
        black = sum(1 for b in mid if b < 5) / len(mid)
        mostly_blank = white > 0.95 or black > 0.95

    status = "PASS"
    notes: list[str] = []
    if width < 1200 or height < 700:
        notes.append(f"section crop {width}x{height} (viewport section, not full page)")
    if size_kb < 5:
        status = "WARN"
        notes.append("very small file")
    if mostly_blank:
        status = "FAIL"
        notes.append("mostly blank")
    elif var_score < 50:
        status = "WARN"
        notes.append(f"low variance {var_score:.1f}")

    return {
        "exists": True,
        "valid_png": True,
        "width": width,
        "height": height,
        "size_kb": size_kb,
        "var_score": round(var_score, 1),
        "status": status,
        "notes": "; ".join(notes) or "ok",
    }


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR
    print(f"Validating screenshots in {target}")
    print(f"{'filename':<50} {'status':<6} {'dims':<12} {'kb':<8} notes")
    print("-" * 110)

    failures = 0
    for name in EXPECTED:
        info = analyze_png(target / name)
        if info.get("status") == "FAIL":
            failures += 1
        dims = f"{info.get('width', '-')}x{info.get('height', '-')}"
        print(
            f"{name:<50} {info.get('status', 'FAIL'):<6} {dims:<12} "
            f"{str(info.get('size_kb', '-')):<8} {info.get('notes', '')}"
        )

    print("-" * 110)
    if failures:
        print(f"OVERALL: FAIL ({failures} file(s))")
        return 1
    print("OVERALL: PASS (section crops may WARN on width; documented in screenshot-index)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
