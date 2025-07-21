import json
import os

import aio_pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")


async def emit_event(routing_key: str, message: dict) -> None:
    """Publish a JSON event to RabbitMQ using a topic exchange."""
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
