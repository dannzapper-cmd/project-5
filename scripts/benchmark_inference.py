#!/usr/bin/env python3
"""Lightweight ONNX Runtime inference benchmark for Phase 2 evidence."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "onnx"
METADATA_DIR = ROOT / "models" / "metadata"
REPORT_PATH = ROOT / "docs" / "evidence" / "phase2-inference-benchmark.md"

WARMUP_RUNS = 20
BENCHMARK_RUNS = 200


@dataclass
class BenchmarkResult:
    model_name: str
    model_version: str
    total_runs: int
    p50_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float


def _load_metadata(filename: str) -> dict:
    path = METADATA_DIR / filename.replace(".onnx", ".json")
    return json.loads(path.read_text())


def benchmark_model(onnx_path: Path, metadata: dict) -> BenchmarkResult:
    """Run warmup + measured inference benchmark for one model."""
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = metadata["input_name"]
    shape = metadata["input_shape"]
    sample_input = np.zeros(shape, dtype=np.float32)

    for _ in range(WARMUP_RUNS):
        session.run(None, {input_name: sample_input})

    latencies: list[float] = []
    for _ in range(BENCHMARK_RUNS):
        t0 = time.perf_counter()
        session.run(None, {input_name: sample_input})
        latencies.append((time.perf_counter() - t0) * 1000)

    arr = np.array(latencies)
    return BenchmarkResult(
        model_name=metadata["model_name"],
        model_version=metadata["model_version"],
        total_runs=BENCHMARK_RUNS,
        p50_ms=float(np.percentile(arr, 50)),
        p95_ms=float(np.percentile(arr, 95)),
        min_ms=float(arr.min()),
        max_ms=float(arr.max()),
        mean_ms=float(arr.mean()),
    )


def run_benchmark() -> dict[str, BenchmarkResult]:
    """Benchmark all ONNX models in models/onnx/."""
    results: dict[str, BenchmarkResult] = {}
    for onnx_file in sorted(MODEL_DIR.glob("*.onnx")):
        metadata = _load_metadata(onnx_file.name)
        results[onnx_file.stem] = benchmark_model(onnx_file, metadata)
    return results


def write_report(results: dict[str, BenchmarkResult]) -> None:
    """Write markdown benchmark report."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 2 Inference Benchmark",
        "",
        "> Synthetic benchmark only. Not representative of production",
        "> hardware. CPU-only inference on developer machine.",
        "> All signals are simulated data, not medical measurements.",
        "",
        "Benchmark conducted on synthetic inputs.",
        "Results are operational performance metrics only,",
        "not clinical accuracy metrics.",
        "",
        f"- Warmup runs: {WARMUP_RUNS}",
        f"- Measured runs per model: {BENCHMARK_RUNS}",
        "",
        "## Results",
        "",
    ]
    for _key, r in results.items():
        lines.extend(
            [
                f"### {r.model_name} ({r.model_version})",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Total runs | {r.total_runs} |",
                f"| p50 latency (ms) | {r.p50_ms:.4f} |",
                f"| p95 latency (ms) | {r.p95_ms:.4f} |",
                f"| min latency (ms) | {r.min_ms:.4f} |",
                f"| max latency (ms) | {r.max_ms:.4f} |",
                f"| mean latency (ms) | {r.mean_ms:.4f} |",
                "",
            ]
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Benchmark report written to {REPORT_PATH}")


def main() -> None:
    if not (MODEL_DIR / "emg_anomaly_v0.onnx").exists():
        print("ERROR: Models not found. Run 'make models-generate' first.", file=sys.stderr)
        sys.exit(1)
    results = run_benchmark()
    write_report(results)
    for r in results.values():
        print(
            f"{r.model_name} {r.model_version}: "
            f"p50={r.p50_ms:.3f}ms p95={r.p95_ms:.3f}ms "
            f"min={r.min_ms:.3f}ms max={r.max_ms:.3f}ms"
        )


if __name__ == "__main__":
    main()
