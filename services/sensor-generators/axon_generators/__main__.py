"""MQTT publisher entrypoint for synthetic sensor generators."""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import aiomqtt

from axon_generators.config import GeneratorConfig
from axon_generators.generator import generate_event_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [sensor-generator] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def publish_loop(config: GeneratorConfig) -> None:
    """Publish synthetic events to MQTT until interrupted."""
    tick = 0
    logger.info(
        "Starting generator scenario=%s mqtt=%s:%s interval=%ss",
        config.scenario,
        config.mqtt_host,
        config.mqtt_port,
        config.axon_publish_interval,
    )

    while True:
        try:
            async with aiomqtt.Client(
                hostname=config.mqtt_host,
                port=config.mqtt_port,
            ) as client:
                logger.info("Connected to MQTT broker")
                while True:
                    batch = generate_event_batch(config, tick)
                    for topic, event in batch:
                        payload = json.dumps(event.model_dump(mode="json"))
                        await client.publish(topic, payload)
                        logger.info(
                            "published topic=%s signal_type=%s quality=%.3f event_id=%s",
                            topic,
                            event.signal_type,
                            event.quality,
                            event.event_id,
                        )
                    tick += 1
                    await asyncio.sleep(config.axon_publish_interval)
        except aiomqtt.MqttError as exc:
            logger.warning("MQTT error: %s — reconnecting in 2s", exc)
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error: %s — reconnecting in 2s", exc)
            await asyncio.sleep(2)


def main() -> None:
    config = GeneratorConfig()
    try:
        asyncio.run(publish_loop(config))
    except KeyboardInterrupt:
        logger.info("Generator stopped")


if __name__ == "__main__":
    main()
