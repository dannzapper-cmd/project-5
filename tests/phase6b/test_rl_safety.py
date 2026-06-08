"""Phase 6B safety / no-claims / dependency-isolation / freeze tests.

File-based checks only (no heavy imports) so they run in core CI.

Synthetic RL operational policy. No real patient data. No medical decisions.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RL_PKG = ROOT / "apps" / "learning" / "rl"

EXACT_DISCLAIMER = (
    "Synthetic RL operational policy. No real patient data. No medical decisions. "
    "Human review required for high-risk actions."
)

# Banned as POSITIVE claims. Safety language that *negates* these (e.g. "no
# diagnosis", "does not treat") is required and legitimate, so we ban only
# phrasings that would only appear as a capability claim — matching the narrow
# set used by ``scripts/verify_phase6a.sh``.
BANNED_TERMS = (
    "medical-grade",
    "medical grade",
    "clinical decision",
    "patient outcome",
    "patient monitoring",
    "treatment recommendation",
    "autonomous clinical",
    "hospital-ready",
    "hospital deployment",
    "real robotic control",
)


def test_disclaimer_exact_text_in_schema():
    schema_src = (ROOT / "apps" / "api" / "app" / "schemas" / "rl.py").read_text()
    assert EXACT_DISCLAIMER in schema_src


def test_disclaimer_exact_text_in_dashboard():
    html = (ROOT / "apps" / "dashboard" / "index.html").read_text()
    assert EXACT_DISCLAIMER in html


def test_disclaimer_module_matches_exact_text():
    src = (RL_PKG / "disclaimer.py").read_text()
    # The DISCLAIMER constant must reconstruct the exact wording.
    assert "Synthetic RL operational policy." in src
    assert "No real patient data." in src
    assert "No medical decisions." in src
    assert "Human review required for high-risk actions." in src


def test_no_banned_safety_terms_in_rl_sources():
    paths = [
        RL_PKG,
        ROOT / "apps" / "api" / "app" / "routes" / "rl.py",
        ROOT / "apps" / "api" / "app" / "schemas" / "rl.py",
        ROOT / "apps" / "api" / "app" / "learning" / "rl_service.py",
        ROOT / "scripts" / "run_rl_micro_module.py",
    ]
    files: list[Path] = []
    for p in paths:
        files.extend(p.glob("*.py") if p.is_dir() else [p])
    for f in files:
        text = f.read_text().lower()
        for term in BANNED_TERMS:
            assert term not in text, f"banned term {term!r} found in {f.name}"


def test_no_real_data_or_network_access_in_rl_package():
    forbidden = ("requests.get", "urllib.request", "http://", "https://", "kaggle", "physionet")
    for py in RL_PKG.glob("*.py"):
        text = py.read_text().lower()
        for token in forbidden:
            assert token.lower() not in text, f"forbidden token {token!r} in {py.name}"


def test_learning_deps_not_in_core_requirements():
    """gymnasium / stable-baselines3 must NOT leak into core deps (item 6B-5)."""
    pyproject = (ROOT / "pyproject.toml").read_text()
    core_block = pyproject.split("[project.optional-dependencies]")[0]
    for dep in ("gymnasium", "stable-baselines3", "stable_baselines3"):
        assert dep not in core_block, f"{dep} leaked into core dependencies"


def test_rl_module_does_not_import_ros2():
    """The RL module must not import ROS2 / Nav2 / SLAM runtime code.

    (Scope-boundary *mentions* in docstrings are fine; we check for real imports
    and node/topic usage, which would indicate functional coupling.)
    """
    forbidden = ("import rclpy", "from rclpy", "rclpy.", "nav2_", "slam_toolbox")
    for py in RL_PKG.glob("*.py"):
        text = py.read_text().lower()
        for token in forbidden:
            assert token not in text, f"ROS2/Nav2/SLAM import {token!r} in {py.name}"


def test_rl_artifacts_path_does_not_collide_with_federated():
    cfg = (RL_PKG / "config.py").read_text()
    assert "federated_report" not in cfg
    assert '"rl"' in cfg or "/ \"rl\"" in cfg or "'rl'" in cfg
