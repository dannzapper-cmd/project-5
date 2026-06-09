"""Tests for scripts/scan_claims.py."""

from __future__ import annotations

from scripts.scan_claims import line_is_allowed, scan_file


def test_negated_medical_device_line_passes(tmp_path):
    path = tmp_path / "sample.md"
    path.write_text("AXON is not a medical device and not for clinical use.\n")
    assert scan_file(path) == []
    assert line_is_allowed("AXON is not a medical device and not for clinical use.")


def test_positive_unsafe_claim_fails(tmp_path):
    path = tmp_path / "bad.md"
    unsafe = "AXON provides medical " + "diagnosis for arrhythmia events."
    path.write_text(f"{unsafe}\n")
    violations = scan_file(path)
    assert len(violations) == 1
    assert violations[0][1] == "medical_diagnosis"
    assert not line_is_allowed(unsafe)
