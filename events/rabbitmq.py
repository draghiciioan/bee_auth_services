import json
import logging
import asyncio

import aio_pika

from utils.settings import settings

RABBITMQ_URL = settings.rabbitmq_url

logger = logging.getLogger(__name__)

_connection_lock = asyncio.Lock()
_connection: aio_pika.RobustConnection | None = None
_channel: aio_pika.abc.AbstractRobustChannel | None = None
_exchange: aio_pika.abc.AbstractRobustExchange | None = None


async def _get_exchange() -> aio_pika.abc.AbstractRobustExchange:
    """Return an open exchange, creating the connection if needed."""

    global _connection, _channel, _exchange

    async with _connection_lock:
        if _exchange and getattr(_exchange, "is_closed", False) is False:
            return _exchange

        if not _connection or getattr(_connection, "is_closed", False):
            _connection = await aio_pika.connect_robust(RABBITMQ_URL)

        if not _channel or getattr(_channel, "is_closed", False):
            _channel = await _connection.channel()

        _exchange = await _channel.declare_exchange(
            "bee.auth.events", aio_pika.ExchangeType.TOPIC
        )
        return _exchange


async def _reset_connection() -> None:
    """Close and clear the cached connection and channel."""

    global _connection, _channel, _exchange

    if _connection and getattr(_connection, "is_closed", False) is False:
        await _connection.close()

    _connection = None
    _channel = None
    _exchange = None


async def emit_event(
    routing_key: str,
    message: dict,
    retries: int = 3,
    delay: float = 1.0,
) -> None:
    """Publish a JSON event to RabbitMQ using a topic exchange."""

    for attempt in range(1, retries + 1):
        try:
            exchange = await _get_exchange()
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
            await _reset_connection()
            if attempt == retries:
                raise
            await asyncio.sleep(delay)

