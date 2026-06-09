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


def test_operational_diagnostics_passes(tmp_path):
    path = tmp_path / "ops.md"
    line = "The service diagnostics endpoint reports operational status only."
    path.write_text(f"{line}\n")
    assert scan_file(path) == []
    assert line_is_allowed(line)


def test_medical_grade_monitoring_fails(tmp_path):
    path = tmp_path / "bad.md"
    line = "AXON provides medical-grade monitoring for simulated sessions."
    path.write_text(f"{line}\n")
    violations = scan_file(path)
    assert len(violations) == 1
    assert violations[0][1] == "medical_grade"
    assert not line_is_allowed(line)


def test_does_not_diagnose_or_treat_passes(tmp_path):
    path = tmp_path / "safe.md"
    line = "AXON does not diagnose or treat any condition."
    path.write_text(f"{line}\n")
    assert scan_file(path) == []
    assert line_is_allowed(line)


def test_diagnoses_arrhythmia_fails(tmp_path):
    path = tmp_path / "bad.md"
    line = "AXON diagnoses arrhythmia from synthetic telemetry."
    path.write_text(f"{line}\n")
    violations = scan_file(path)
    assert len(violations) == 1
    assert violations[0][1] == "medical_diagnosis"
    assert not line_is_allowed(line)
