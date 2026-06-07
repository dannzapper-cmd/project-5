"""Generate Phase 3 evidence artifacts (offline)."""

from __future__ import annotations

import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_nominal_state():
    from apps.api.app.agents.service import build_initial_state

    now = datetime.now(UTC).isoformat()
    return build_initial_state(
        "session-synthetic-001",
        "trace-evidence-nominal",
        {
            "emg": {"timestamp": now, "quality": 0.95, "values": [0.1]},
            "imu": {"timestamp": now, "quality": 0.92, "values": [0.0]},
            "ecg_like": {"timestamp": now, "quality": 0.9, "values": [0.5]},
            "spo2_proxy": {"timestamp": now, "quality": 0.88, "values": [0.98]},
        },
        {
            "emg_anomaly": {
                "score": 0.1,
                "confidence": 0.9,
                "output_label": "normal",
                "timestamp": now,
            },
        },
    )


def build_hitl_state():
    from apps.api.app.agents.service import build_initial_state

    now = datetime.now(UTC).isoformat()
    state = build_initial_state(
        "session-synthetic-001",
        "trace-evidence-hitl",
        {"emg": {"timestamp": now, "quality": 0.95, "values": [0.1]}},
        {
            "emg_anomaly": {
                "score": 0.95,
                "confidence": 0.2,
                "output_label": "elevated",
                "timestamp": now,
            },
        },
    )
    state["risk_level"] = "high"
    state["confidence"] = 0.2
    state["proposed_action"] = "pause_simulation"
    return state


def generate_graph_mermaid(out_path: Path) -> None:
    from apps.api.app.agents.graph import get_compiled_graph

    graph = get_compiled_graph()
    mermaid_str = graph.get_graph().draw_mermaid()
    out_path.write_text(f"# AXON Phase 3 Agent Graph\n\n```mermaid\n{mermaid_str}\n```\n")
    print(f"Wrote {out_path}")


def generate_trace_sample(out_path: Path) -> None:
    import json

    from apps.api.app.agents.graph import get_compiled_graph

    graph = get_compiled_graph()
    state = build_hitl_state()
    state["risk_level"] = "high"
    state["confidence"] = 0.8
    result = graph.invoke(state)
    traces = []
    for t in result.get("trace_events", []):
        traces.append(
            {
                "agent_name": t.get("agent_name"),
                "stage": t.get("stage"),
                "confidence": t.get("confidence"),
                "risk_level": t.get("risk_level"),
                "duration_ms": t.get("duration_ms"),
            }
        )
    payload = {
        "description": "HITL branch graph execution (high simulated risk)",
        "trace_id": result.get("trace_id"),
        "requires_human_confirmation": result.get("requires_human_confirmation"),
        "decision_status": (result.get("decision_event") or {}).get("status"),
        "agent_traces": traces,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out_path}")


def generate_benchmarks(out_path: Path, runs: int = 20) -> None:
    from apps.api.app.agents.graph import get_compiled_graph

    graph = get_compiled_graph()
    times_ms: list[float] = []
    for _ in range(runs):
        state = build_nominal_state()
        t0 = time.monotonic()
        graph.invoke(state)
        times_ms.append((time.monotonic() - t0) * 1000)

    p50 = statistics.median(times_ms)
    sorted_t = sorted(times_ms)
    p95_idx = max(0, int(len(sorted_t) * 0.95) - 1)
    p95 = sorted_t[p95_idx]

    content = f"""# Phase 3 Agent Graph Benchmarks (Mock Mode)

Runs: {runs}
Environment: offline mock LLM, no Redis

| Metric | Value (ms) |
|--------|------------|
| p50    | {p50:.2f} |
| p95    | {p95:.2f} |
| min    | {min(times_ms):.2f} |
| max    | {max(times_ms):.2f} |

Target: p95 < 500ms in mock mode — {"PASS" if p95 < 500 else "REVIEW"}
"""
    out_path.write_text(content)
    print(f"Wrote {out_path} (p50={p50:.2f}ms, p95={p95:.2f}ms)")


def main() -> None:
    evidence_dir = ROOT / "docs" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    generate_graph_mermaid(evidence_dir / "phase-3-agent-graph.md")
    generate_trace_sample(evidence_dir / "phase-3-trace-sample.json")
    generate_benchmarks(evidence_dir / "phase-3-benchmarks.md")


if __name__ == "__main__":
    main()
