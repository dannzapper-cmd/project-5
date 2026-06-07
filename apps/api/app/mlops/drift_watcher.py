"""Background drift detector task (reads model score confidences)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from redis.asyncio import Redis

from apps.api.app.mlops.state import mlops_state
from apps.api.app.schemas.events import DriftEventV1
from apps.api.app.telemetry.model_score_streams import MODEL_SCORE_STREAM
from apps.mlops.config import DRIFT_CHECK_INTERVAL, DRIFT_STREAM
from apps.mlops.drift import SlidingWindowDriftDetector

logger = logging.getLogger(__name__)

_detectors: dict[str, SlidingWindowDriftDetector] = {
    "emg": SlidingWindowDriftDetector(),
    "imu": SlidingWindowDriftDetector(),
}


async def drift_detector_loop(redis: Redis | None) -> None:
    """Periodic drift check on model score stream confidences."""
    if redis is None:
        return

    last_id = "$"
    interval = DRIFT_CHECK_INTERVAL

    while True:
        try:
            events = await redis.xread(
                streams={MODEL_SCORE_STREAM: last_id},
                block=1000,
                count=20,
            )
            if events:
                for _stream, messages in events:
                    for msg_id, data in messages:
                        last_id = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                        raw = data.get(b"payload") or data.get("payload")
                        if raw is None:
                            continue
                        if isinstance(raw, bytes):
                            raw = raw.decode()
                        payload = json.loads(raw)
                        confidence = float(payload.get("confidence", 0.0))
                        signal = payload.get("metadata", {}).get("signal_type", "emg")
                        if signal in _detectors:
                            _detectors[signal].update(confidence)

            await asyncio.sleep(interval)
            result = _detectors["emg"].check()
            mlops_state.drift_status = result["drift_status"]
            mlops_state.drift_score = result.get("drift_score")
            mlops_state.drift_recommendation = result["recommendation"]
            mlops_state.last_drift_check_at = datetime.now(UTC).isoformat()

            if result["drift_status"] == "drift_detected":
                event = DriftEventV1(
                    trace_id="drift-detector",
                    source="drift_detector",
                    session_id="simulated-rehab-session",
                    signal_type="emg",
                    threshold=result["threshold"],
                    drift_status=result["drift_status"],
                    drift_score=result.get("drift_score"),
                    evidence_window=result["evidence_window"],
                    mean_confidence=result.get("mean_confidence"),
                    recommendation=result["recommendation"],
                )
                mlops_state.last_drift_event_id = event.event_id
                await redis.xadd(
                    DRIFT_STREAM,
                    {"payload": event.model_dump_json()},
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("drift_detector error: %s", exc)
            await asyncio.sleep(2)
