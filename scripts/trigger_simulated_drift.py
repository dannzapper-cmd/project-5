#!/usr/bin/env python3
"""Inject low-confidence model scores to trigger simulated drift."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from uuid import uuid4

try:
    import redis
except ImportError:
    print("redis package required", file=sys.stderr)
    sys.exit(1)

STREAM = "axon:v1:stream:model_scores"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    args = parser.parse_args()

    r = redis.Redis.from_url(args.redis_url, decode_responses=False)
    for i in range(args.count):
        event = {
            "schema_version": "v1",
            "event_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "trace_id": "drift-sim-inject",
            "source": "drift-simulator",
            "model_name": "emg_anomaly",
            "model_version": "v0",
            "score": 0.3,
            "confidence": args.confidence,
            "latency_ms": 1.5,
            "input_event_id": f"sim-{i}",
            "output_label": "elevated_activity",
            "metadata": {"signal_type": "emg", "scenario": "low_confidence_drift"},
        }
        r.xadd(STREAM, {"payload": json.dumps(event)})
        time.sleep(0.05)
    print(f"Injected {args.count} low-confidence scores to {STREAM}")


if __name__ == "__main__":
    main()
