#!/usr/bin/env python3
"""Phase 10A — capture real dashboard screenshots via Playwright/Chromium."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:3000")
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
WARMUP_MS = int(os.environ.get("SCREENSHOT_WARMUP_MS", "30000"))
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
OUT_DIR = ROOT / "docs/evidence/phase10/demo/screenshots" / TIMESTAMP
LATEST_DIR = ROOT / "docs/evidence/phase10/demo/screenshots/latest"

SHOTS = [
    ("00_dashboard_overview.png", "connection-status", "Dashboard overview / connection status"),
    ("01_live_telemetry_streams.png", "live-telemetry", "Live telemetry streams"),
    ("02_edge_inference_and_fusion.png", "edge-inference", "Edge inference / model scores"),
    ("03_agent_traces_and_hitl.png", "agent-traces", "Agent traces and HITL context"),
    ("04_digital_twin_state_mirror.png", "digital-twin", "Digital twin state mirror"),
    ("05_evidence_center_or_observability.png", "operational-status", "Operational status / evidence"),
    ("06_failure_or_degraded_mode_if_available.png", "failure-injection", "Failure injection panel"),
    ("07_ros2_nav_slam_compose_status_if_available.png", "nav-slam", "Nav2/SLAM MiniLab offline panel"),
]


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *cmd.split()],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def docker_profiles() -> str:
    try:
        out = subprocess.check_output(
            ["docker", "compose", "--profile", "core", "ps", "--format", "json"],
            cwd=ROOT,
            text=True,
        )
        running = []
        for line in out.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("State") == "running":
                running.append(row.get("Service", "?"))
        return f"core ({', '.join(running)})" if running else "core (not running)"
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return "core (unknown)"


def wait_for_counter(page, selector: str, minimum: int, deadline_ms: int) -> int:
    import time

    deadline = time.time() + deadline_ms / 1000
    while time.time() < deadline:
        text = page.locator(selector).text_content() or "0"
        value = int(text.strip() or "0")
        if value >= minimum:
            return value
        page.wait_for_timeout(1000)
    raise TimeoutError(f"Timeout waiting for {selector} >= {minimum}")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright not installed. Run:\n"
            "  .venv/bin/pip install playwright\n"
            "  .venv/bin/playwright install chromium",
            file=sys.stderr,
        )
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    failed = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_selector('[data-testid="connection-status"]', timeout=30000)

        try:
            wait_for_counter(page, "#event-counter", 5, WARMUP_MS)
            wait_for_counter(page, "#model-score-counter", 3, WARMUP_MS)
        except TimeoutError as err:
            print(f"Warm-up warning: {err}")
            results.append({"note": f"warm-up partial: {err}"})

        for filename, test_id, label in SHOTS:
            dest = OUT_DIR / filename
            try:
                if test_id == "failure-injection":
                    btn = page.locator('button[data-scenario="sensor_dropout"]')
                    if btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(2000)
                if test_id == "operational-status":
                    page.locator('[data-testid="mission-control"]').scroll_into_view_if_needed()

                section = page.locator(f'[data-testid="{test_id}"]')
                section.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                section.screenshot(path=str(dest))
                results.append({"file": filename, "status": "ok", "label": label})
                print(f"Captured {filename}")
            except Exception as err:  # noqa: BLE001
                failed = True
                results.append({"file": filename, "status": "fail", "error": str(err)})
                print(f"Failed {filename}: {err}", file=sys.stderr)

        browser.close()

    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    for filename, _, _ in SHOTS:
        src = OUT_DIR / filename
        if src.exists():
            shutil.copy2(src, LATEST_DIR / filename)

    metadata = {
        "timestamp": TIMESTAMP,
        "git_sha": git("rev-parse HEAD"),
        "branch": git("branch --show-current"),
        "command": ".venv/bin/python scripts/demo/capture_phase10a_screenshots.py",
        "dashboard_url": DASHBOARD_URL,
        "api_base": API_BASE,
        "docker_profiles": docker_profiles(),
        "warmup_ms": WARMUP_MS,
        "screenshots": results,
        "pass": not failed,
        "notes": [
            "ROS2/Nav2/SLAM panel shows offline state under core-only profile — compose-validated.",
            "Screenshots from real local execution; no stock or generated imagery.",
        ],
    }
    (OUT_DIR / "capture-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"\nScreenshots saved to {OUT_DIR}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
