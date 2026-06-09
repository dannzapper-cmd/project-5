#!/usr/bin/env python3
"""Line-by-line scan for unsafe medical/device claims in repository text."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "mlruns",
    "mlartifacts",
    "htmlcov",
}

SCAN_SUFFIXES = {".py", ".md", ".html", ".js", ".sh", ".yml", ".yaml", ".toml", ".txt", ".json"}

# Positive unsafe claims — fail when matched without a qualifier on the same line.
UNSAFE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "medical_diagnosis",
        re.compile(
            r"\bAXON\s+(?:provides\s+)?(?:medical\s+)?diagnos(?:es|is)\b"
            r"|\bdiagnos(?:e|es|is|tic)\b(?=.*\b(?:arrhythmia|clinical|medical|patient|disease|condition)\b)",
            re.I,
        ),
    ),
    ("medical_grade", re.compile(r"\bmedical[- ]grade\b", re.I)),
    (
        "clinical_decision_maker",
        re.compile(r"\b(?:autonomous\s+)?clinical decision[- ]maker\b", re.I),
    ),
    (
        "patient_data",
        re.compile(
            r"\b(?:uses|ingests|stores|processes|trains on|trained on|includes)\s+"
            r"(?:real\s+)?patient data\b|\breal patient data\b",
            re.I,
        ),
    ),
    (
        "regulatory_claim",
        re.compile(r"\b(?:FDA[- ]approved|HIPAA[- ]compliant|HIPAA compliance)\b", re.I),
    ),
    (
        "treatment_claim",
        re.compile(
            r"\btreats?\b(?=.*\b(?:arrhythmia|clinical|medical|patient|disease|condition)\b)"
            r"|\btreatment\b(?=.*\b(?:clinical|medical|patient|disease|condition)\b)",
            re.I,
        ),
    ),
    ("hospital_deployment", re.compile(r"\bhospital deployment\b", re.I)),
]

QUALIFIER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"not a medical device", re.I),
    re.compile(r"not a diagnostic system", re.I),
    re.compile(r"not for clinical use", re.I),
    re.compile(r"not based on real patient data", re.I),
    re.compile(r"not medical diagnosis", re.I),
    re.compile(r"not trained on real patients?", re.I),
    re.compile(r"no medical claims", re.I),
    re.compile(r"does not diagnose", re.I),
    re.compile(r"does not .*diagnose", re.I),
    re.compile(r"does\s+\W*not\W+.*diagnose", re.I),
    re.compile(r"does not diagnose or treat", re.I),
    re.compile(r"\bNOT diagnose\b", re.I),
    re.compile(r"does not treat", re.I),
    re.compile(r"not diagnosis", re.I),
    re.compile(r"claims we avoid", re.I),
    re.compile(r"claim scanner", re.I),
    re.compile(r"claim scan", re.I),
    re.compile(r"scan_claims\.py", re.I),
    re.compile(r"not fine-tuning", re.I),
    re.compile(r"no medical diagnosis", re.I),
    re.compile(r"no .*diagnos", re.I),
    re.compile(r"no diagnosis or treatment", re.I),
    re.compile(r"no treatment advice", re.I),
    re.compile(r"no clinical claims", re.I),
    re.compile(r"no clinical inference", re.I),
    re.compile(r"not for diagnosis", re.I),
    re.compile(r"not for treatment", re.I),
    re.compile(r"synthetic simulation only", re.I),
    re.compile(r"synthetic only", re.I),
    re.compile(r"no real patient data", re.I),
    re.compile(r"without real patient data", re.I),
    re.compile(r"what .* does not do", re.I),
    re.compile(r"out of scope", re.I),
    re.compile(r"not in scope", re.I),
    re.compile(r"must never do", re.I),
    re.compile(r"do not use", re.I),
    re.compile(r"medical claim was added", re.I),
    re.compile(r"prohibited claims", re.I),
    re.compile(r"no claims of", re.I),
    re.compile(r"forbidden claims", re.I),
    re.compile(r"prohibited language", re.I),
    re.compile(r"avoid in code", re.I),
    re.compile(r"what axon does not", re.I),
    re.compile(r"diagnosis of arrhythmia", re.I),
    re.compile(r"re\.compile\(", re.I),
    re.compile(r'banned term|BANNED_TERMS|"hospital deployment"', re.I),
    re.compile(
        r'^\s*["\'](?:medical[- ]grade|clinical decision|patient outcome|'
        r'treatment recommendation|hospital deployment)["\'],?\s*$',
        re.I,
    ),
]

FORBIDDEN_SECTION_MARKERS = re.compile(
    r"Forbidden Claims|Claims We Avoid|Prohibited Language|What AXON Does NOT|"
    r"Out of Scope|Intentionally Not in Scope|must never do|No medical claims",
    re.I,
)
SECTION_BREAK = re.compile(r"^#{1,3}\s+", re.M)


def _iter_scan_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        files.append(path)
    return sorted(files)


def line_is_allowed(line: str) -> bool:
    """Return True when the line has no unsafe claim or is properly qualified."""
    matched: list[str] = []
    for label, pattern in UNSAFE_PATTERNS:
        if pattern.search(line):
            matched.append(label)
    if not matched:
        return True
    return any(q.search(line) for q in QUALIFIER_PATTERNS)


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, rule_id, line_text) violations."""
    violations: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return violations

    in_forbidden_section = False
    for idx, line in enumerate(text.splitlines(), start=1):
        if FORBIDDEN_SECTION_MARKERS.search(line):
            in_forbidden_section = True
            continue
        if SECTION_BREAK.match(line) and not FORBIDDEN_SECTION_MARKERS.search(line):
            in_forbidden_section = False

        if in_forbidden_section:
            continue
        if line_is_allowed(line):
            continue
        for label, pattern in UNSAFE_PATTERNS:
            if pattern.search(line):
                violations.append((idx, label, line.strip()))
                break
    return violations


def scan_paths(paths: list[Path]) -> list[tuple[Path, int, str, str]]:
    """Scan explicit paths or directories."""
    all_files: list[Path] = []
    for path in paths:
        if path.is_dir():
            all_files.extend(_iter_scan_files(path))
        elif path.is_file():
            all_files.append(path)
    results: list[tuple[Path, int, str, str]] = []
    for file_path in sorted(set(all_files)):
        for line_no, rule_id, line in scan_file(file_path):
            results.append((file_path, line_no, rule_id, line))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan AXON repo for unsafe medical claims")
    parser.add_argument(
        "paths",
        nargs="*",
        default=[
            "apps",
            "docs",
            "scripts",
            "services",
            "README.md",
            "ROADMAP.md",
            "PROJECT_CONTEXT.md",
        ],
        help="Files or directories to scan (default: core text sources)",
    )
    args = parser.parse_args(argv)

    scan_roots = [ROOT / p if not Path(p).is_absolute() else Path(p) for p in args.paths]
    violations = scan_paths(scan_roots)
    if not violations:
        print("PASS: no unsafe medical/device claims detected")
        return 0

    print("FAIL: unsafe medical/device claims detected:")
    for file_path, line_no, rule_id, line in violations:
        rel = file_path.relative_to(ROOT) if file_path.is_relative_to(ROOT) else file_path
        print(f"  {rel}:{line_no} [{rule_id}] {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
