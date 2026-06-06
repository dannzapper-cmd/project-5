#!/usr/bin/env python3
"""Publish replay scenario events to MQTT from JSONL files."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import aiomqtt
from apps.api.app.schemas.events import SensorEventV1

logging.basicConfig(level=logging.INFO, format="%(asctime)s [replay] %(message)s")
logger = logging.getLogger(__name__)


async def publish_file(
    path: Path,
    *,
    mqtt_host: str,
    mqtt_port: int,
    speed: float,
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    published = 0
    skipped = 0

    async with aiomqtt.Client(hostname=mqtt_host, port=mqtt_port) as client:
        for line_no, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                event = SensorEventV1.model_validate(record["event"])
                topic = record["topic"]
            except Exception as exc:
                skipped += 1
                logger.warning("Line %s invalid, skipping: %s", line_no, exc)
                continue

            payload = json.dumps(event.model_dump(mode="json"))
            await client.publish(topic, payload)
            published += 1
            logger.info(
                "Published topic=%s signal=%s event_id=%s",
                topic,
                event.signal_type,
                event.event_id,
            )
            await asyncio.sleep(speed)

    logger.info("Replay complete file=%s published=%s skipped=%s", path.name, published, skipped)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish AXON replay scenario to MQTT")
    parser.add_argument("--file", required=True, help="Path to JSONL scenario file")
    parser.add_argument("--speed", type=float, default=0.5, help="Seconds between events")
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        logger.error("File not found: %s", path)
        sys.exit(1)

    asyncio.run(
        publish_file(
            path,
            mqtt_host=args.mqtt_host,
            mqtt_port=args.mqtt_port,
            speed=args.speed,
        )
    )


if __name__ == "__main__":
    main()
