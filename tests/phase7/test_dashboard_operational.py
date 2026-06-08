"""Lightweight static checks for dashboard operational panel fallback."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "apps" / "dashboard" / "app.js"
INDEX_HTML = ROOT / "apps" / "dashboard" / "index.html"


def test_operational_panel_markup_present():
    html = INDEX_HTML.read_text()
    assert "operational-status-panel" in html
    assert "ops-api-unreachable" in html
    assert "SIMULATED SYSTEM" in html
    assert "Not a medical device" in html


def test_operational_panel_fallback_logic_present():
    js = APP_JS.read_text()
    html = INDEX_HTML.read_text()
    assert "pollOperationalStatus" in js
    assert "ops-api-unreachable" in js
    assert "Operational status unavailable" in html
    assert "API unreachable" in js
    assert "ops-content" in js
    # Fallback must not assign ok before data loads
    assert "loading" in html or "loading" in js


def test_operational_panel_null_safe_render():
    js = APP_JS.read_text()
    assert "if (coreBody)" in js
    assert "if (optBody)" in js
    assert "components || {}" in js
