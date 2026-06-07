"""Data card and model card markdown generation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from apps.mlops.config import EMG_LABELS


def write_data_card(metadata: dict, dataset: dict, output_path: Path) -> None:
    """Write markdown data card per Phase 4 template."""
    dataset_id = metadata["dataset_id"]
    scenarios = metadata.get("scenario", metadata.get("scenarios", []))
    if isinstance(scenarios, str):
        scenarios = [scenarios]

    emg_counts = Counter(dataset["emg"]["labels"])
    total = sum(emg_counts.values()) or 1

    lines = [
        f"# Data Card: {dataset_id}",
        "",
        "## Overview",
        "- Type: Synthetic signal dataset",
        f"- Generator version: {metadata['generator_version']}",
        f"- Created at: {metadata['created_at']}",
        f"- Seed: {metadata['seed']}",
        f"- Scenarios: {', '.join(scenarios)}",
        "- Signal types: emg, imu",
        f"- Row count: {metadata['row_count']}",
        "",
        "## Synthetic Only",
        "All data is synthetically generated. No real patient data. No real sensor hardware.",
        "",
        "## Prohibited Use",
        "Not for clinical use. Not for medical diagnosis. Not for treatment decisions.",
        "",
        "## Label Distribution (EMG)",
        "| Label   | Count | Percentage |",
        "|---------|-------|------------|",
    ]
    for label in EMG_LABELS:
        count = emg_counts.get(label, 0)
        pct = 100.0 * count / total
        lines.append(f"| {label}  | {count}   | {pct:.1f}%        |")

    lines.extend(
        [
            "",
            "## Feature Description",
            "**EMG** (extract_emg_features): rms, zcr, variance, peak2peak, mean_abs",
            "**IMU** (extract_imu_features): range_x, range_y, range_z, jerk, mean_mag",
            "",
            "## Limitations",
            "Synthetic windows only. Label mapping from scenario templates, "
            "not ground-truth physiology.",
            "Small default size suitable for laptop smoke runs.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines))


def write_model_card(
    signal_type: str,
    version: str,
    dataset_id: str,
    metrics: dict,
    promotion_status: str,
    architecture: str,
    output_path: Path,
) -> None:
    """Write markdown model card per Phase 4 template."""
    lines = [
        f"# Model Card: {signal_type} {version}",
        "",
        "## Model Details",
        f"- Signal type: {signal_type}",
        f"- Version: {version}",
        f"- Architecture: {architecture}",
        f"- Trained on dataset: {dataset_id}",
        f"- Promotion status: {promotion_status}",
        "",
        "## Synthetic Only",
        "Trained exclusively on synthetic biomedical-inspired signals. No real patient data.",
        "",
        "## Intended Use",
        "Simulated edge inference for portfolio demonstration.",
        "",
        "## Out of Scope",
        "Clinical use. Medical diagnosis. Treatment decisions. Real patient monitoring.",
        "",
        "## Performance Metrics",
        "| Metric          | Value |",
        "|-----------------|-------|",
        f"| Accuracy        | {metrics.get('accuracy', '—')} |",
        f"| F1-macro        | {metrics.get('f1_macro', '—')} |",
        f"| Latency p50 ms  | {metrics.get('latency_p50_ms', '—')} |",
        f"| Latency p95 ms  | {metrics.get('latency_p95_ms', '—')} |",
        "",
        "## Limitations",
        "Lightweight logistic regression on statistical features. "
        "Not representative of production edge models.",
        "",
    ]
    output_path.write_text("\n".join(lines))
