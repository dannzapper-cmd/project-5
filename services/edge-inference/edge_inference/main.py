"""Edge inference service entrypoint."""

from __future__ import annotations

import asyncio
import logging
import signal

from redis.asyncio import Redis

from edge_inference.config import settings
from edge_inference.model_registry import ModelRegistry
from edge_inference.redis_consumer import consumer_loop, metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [edge-inference] %(message)s",
)
logger = logging.getLogger(__name__)


async def main_async() -> None:
    logger.info("Starting edge-inference (%s)", settings.axon_phase)
    registry = ModelRegistry(settings.model_dir, settings.metadata_dir)
    logger.info("Loaded models for signals: %s", registry.supported_signals())

    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    await redis.ping()
    logger.info("Redis connected: %s", settings.redis_url)

    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    consumer_task = asyncio.create_task(consumer_loop(redis, registry))

    await stop_event.wait()
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

    summary = metrics.summary()
    logger.info("Shutdown metrics: %s", summary)
    await redis.aclose()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
