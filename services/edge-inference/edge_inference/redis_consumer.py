"""Redis Streams consumer for sensor events and model score publishing."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from redis.asyncio import Redis

from apps.api.app.schemas.events import ModelScoreEventV1, SensorEventV1

from edge_inference.config import settings
from edge_inference.model_registry import ModelRegistry
from edge_inference.onnx_runner import OnnxRunner
from edge_inference.preprocess import preprocess_sensor_event
from edge_inference.scoring import build_model_score_event

logger = logging.getLogger(__name__)

STREAM_MAXLEN = 1000

# Phase 2: XREAD (not consumer groups) — single consumer, simpler restart semantics.
SIGNAL_TYPE_FROM_STREAM: dict[str, str] = {
    settings.emg_stream: "emg",
    settings.imu_stream: "imu",
}


class InferenceMetrics:
    """Lightweight in-memory latency metrics."""

    def __init__(self) -> None:
        self.latencies: list[float] = []
        self.total_inferences: int = 0
        self.per_model_counts: dict[str, int] = {}

    def record(self, model_name: str, latency_ms: float) -> None:
        self.latencies.append(latency_ms)
        self.total_inferences += 1
        self.per_model_counts[model_name] = self.per_model_counts.get(model_name, 0) + 1

    def summary(self) -> dict[str, Any]:
        if not self.latencies:
            return {
                "total_inferences": 0,
                "per_model_counts": {},
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
            }
        import numpy as np

        arr = np.array(self.latencies)
        return {
            "total_inferences": self.total_inferences,
            "per_model_counts": dict(self.per_model_counts),
            "p50_ms": float(np.percentile(arr, 50)),
            "p95_ms": float(np.percentile(arr, 95)),
            "min_ms": float(arr.min()),
            "max_ms": float(arr.max()),
        }


metrics = InferenceMetrics()


async def append_model_score(redis: Redis, event: ModelScoreEventV1) -> str | None:
    """Append ModelScoreEventV1 to model_scores stream."""
    payload = event.model_dump(mode="json")
    fields = {
        "event_id": event.event_id,
        "timestamp": payload["timestamp"],
        "trace_id": event.trace_id,
        "source": event.source,
        "model_name": event.model_name,
        "payload": json.dumps(payload),
    }
    return await redis.xadd(
        settings.model_score_stream,
        fields,
        maxlen=STREAM_MAXLEN,
        approximate=True,
    )


async def process_sensor_event(
    redis: Redis,
    registry: ModelRegistry,
    runners: dict[str, OnnxRunner],
    raw_payload: str,
    signal_type: str,
) -> None:
    """Validate sensor event, run inference, publish model score."""
    try:
        data = json.loads(raw_payload)
        sensor_event = SensorEventV1.model_validate(data)
    except Exception as exc:
        logger.warning("Invalid sensor event payload: %s", exc)
        return

    if sensor_event.signal_type != signal_type:
        logger.warning(
            "Signal type mismatch: stream=%s event=%s",
            signal_type,
            sensor_event.signal_type,
        )
        return

    entry = registry.get_for_signal(signal_type)
    if entry is None:
        return

    metadata, _path = entry
    runner = runners[signal_type]
    input_array = preprocess_sensor_event(sensor_event, metadata)
    inference = runner.run(input_array)
    score_event = build_model_score_event(
        sensor_event, metadata, inference, source=settings.source
    )
    metrics.record(metadata.model_name, inference.latency_ms)
    await append_model_score(redis, score_event)
    logger.debug(
        "Scored %s: score=%.3f label=%s latency=%.2fms",
        metadata.model_name,
        inference.score,
        inference.label,
        inference.latency_ms,
    )


async def consumer_loop(redis: Redis, registry: ModelRegistry) -> None:
    """Read sensor streams with XREAD BLOCK; score independently per signal."""
    runners: dict[str, OnnxRunner] = {}
    for signal_type in registry.supported_signals():
        meta, path = registry.get_for_signal(signal_type)  # type: ignore[misc]
        runners[signal_type] = OnnxRunner(meta, str(path))

    streams = {settings.emg_stream: "$", settings.imu_stream: "$"}
    # On startup, last_id="$" — only new events from now forward (no stale replay).

    while True:
        try:
            events = await redis.xread(
                streams=streams,
                block=1000,
                count=10,
            )
            if events:
                for stream_key, messages in events:
                    stream_name = stream_key.decode() if isinstance(stream_key, bytes) else stream_key
                    signal_type = SIGNAL_TYPE_FROM_STREAM.get(stream_name)
                    if signal_type is None:
                        continue
                    for msg_id, msg_data in messages:
                        streams[stream_name] = (
                            msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                        )
                        raw = msg_data.get(b"payload") or msg_data.get("payload")
                        if raw is None:
                            continue
                        if isinstance(raw, bytes):
                            raw = raw.decode()
                        await process_sensor_event(
                            redis, registry, runners, raw, signal_type
                        )

            await asyncio.sleep(settings.inference_interval_ms / 1000)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Redis consumer error: %s", exc)
            await asyncio.sleep(2)
