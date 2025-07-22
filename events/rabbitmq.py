import json
import os
import logging
import asyncio

import aio_pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")

logger = logging.getLogger(__name__)


async def emit_event(
    routing_key: str,
    message: dict,
    retries: int = 3,
    delay: float = 1.0,
) -> None:
    """Publish a JSON event to RabbitMQ using a topic exchange."""

    for attempt in range(1, retries + 1):
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange(
                    "bee.auth.events",
                    aio_pika.ExchangeType.TOPIC,
                )
                await exchange.publish(
                    aio_pika.Message(body=json.dumps(message).encode()),
                    routing_key=routing_key,
                )
                logger.info(
                    "event_published",
                    extra={
                        "endpoint": "rabbitmq",
                        "user_id": message.get("user_id"),
                    },
                )
            break
        except Exception:  # pragma: no cover - executed in tests
            logger.exception(
                "Failed to publish event '%s' on attempt %s", routing_key, attempt
            )
            if attempt == retries:
                raise
            await asyncio.sleep(delay)
