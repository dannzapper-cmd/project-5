#!/usr/bin/env python3
"""Phase 10C-2A — capture interactive dashboard UX screenshots via Playwright.

Separate from the Phase 10A capture script: it targets the new demo-cockpit
panels and does NOT overwrite Phase 10A screenshots. Output goes to
docs/evidence/phase10/dashboard-ux/screenshots/.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:3000")
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
WARMUP_MS = int(os.environ.get("SCREENSHOT_WARMUP_MS", "30000"))
TIMESTAMP = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
OUT_DIR = ROOT / "docs/evidence/phase10/dashboard-ux/screenshots" / TIMESTAMP
LATEST_DIR = ROOT / "docs/evidence/phase10/dashboard-ux/screenshots/latest"

# (filename, css_selector, label, pre_action)
SHOTS = [
    ("00_demo_cockpit_top.png", '[data-testid="demo-cockpit"]', "Live Demo Cockpit guide", None),
    (
        "01_backend_proof_action_log.png",
        '[data-testid="backend-proof"]',
        "Backend proof panel",
        None,
    ),
    (
        "02_failure_injection_visible_effect.png",
        "#safety-panel",
        "Failure injection effect on safety",
        "inject_low_conf",
    ),
    ("03_hitl_decision_flow.png", '[data-testid="hitl"]', "HITL / safety gate", None),
    (
        "04_digital_twin_command_feedback.png",
        '[data-testid="digital-twin"]',
        "Digital twin command feedback",
        "twin_pause",
    ),
    (
        "05_learning_evidence_panels.png",
        "#federated-learning-panel",
        "Learning evidence panels",
        None,
    ),
    (
        "06_robotics_lab_profile_boundary.png",
        '[data-testid="nav-slam"]',
        "Robotics Lab profile boundary",
        None,
    ),
    ("07_guided_demo_mode.png", "body", "Guided demo overlay", "guided_demo"),
]


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), *cmd.split()], text=True).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def wait_for_counter(page, selector: str, minimum: int, deadline_ms: int) -> int:
    import time

    deadline = time.time() + deadline_ms / 1000
    while time.time() < deadline:
        text = page.locator(selector).text_content() or "0"
        try:
            value = int(text.strip() or "0")
        except ValueError:
            value = 0
        if value >= minimum:
            return value
        page.wait_for_timeout(1000)
    raise TimeoutError(f"Timeout waiting for {selector} >= {minimum}")


def run_pre_action(page, action: str) -> None:
    if action == "inject_low_conf":
        btn = page.locator('button[data-scenario="model_low_confidence"]')
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(2500)
    elif action == "twin_pause":
        btn = page.locator("#twin-cmd-pause")
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(2000)
    elif action == "guided_demo":
        btn = page.locator("#guided-demo-start")
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(1200)


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
        page.wait_for_selector('[data-testid="demo-cockpit"]', timeout=30000)

        try:
            wait_for_counter(page, "#event-counter", 5, WARMUP_MS)
            wait_for_counter(page, "#model-score-counter", 3, WARMUP_MS)
        except TimeoutError as err:
            print(f"Warm-up warning: {err}")
            results.append({"note": f"warm-up partial: {err}"})

        for filename, selector, label, pre_action in SHOTS:
            dest = OUT_DIR / filename
            try:
                if pre_action:
                    run_pre_action(page, pre_action)
                if selector == "body":
                    page.screenshot(path=str(dest))
                else:
                    section = page.locator(selector)
                    section.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    section.screenshot(path=str(dest))
                results.append({"file": filename, "status": "ok", "label": label})
                print(f"Captured {filename}")
            except Exception as err:  # noqa: BLE001
                failed = True
                results.append({"file": filename, "status": "fail", "error": str(err)})
                print(f"Failed {filename}: {err}", file=sys.stderr)

        # Leave the system in a clean state.
        try:
            page.locator("#guided-demo-end").click(timeout=2000)
            page.locator("#injection-reset").click(timeout=2000)
        except Exception:  # noqa: BLE001
            pass

        browser.close()

    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    for filename, _, _, _ in SHOTS:
        src = OUT_DIR / filename
        if src.exists():
            shutil.copy2(src, LATEST_DIR / filename)

    metadata = {
        "timestamp": TIMESTAMP,
        "git_sha": git("rev-parse HEAD"),
        "branch": git("branch --show-current"),
        "command": ".venv/bin/python scripts/demo/capture_phase10c2a_dashboard_ux.py",
        "dashboard_url": DASHBOARD_URL,
        "api_base": API_BASE,
        "warmup_ms": WARMUP_MS,
        "screenshots": results,
        "pass": not failed,
        "notes": [
            "Phase 10C-2A interactive dashboard UX captures (separate from Phase 10A).",
            "ROS2/Nav2/SLAM shown offline under core profile; live buttons disabled by design.",
            "Real local execution; no stock or generated imagery.",
        ],
    }
    (OUT_DIR / "capture-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"\nScreenshots saved to {OUT_DIR}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
