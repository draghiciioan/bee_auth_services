import json
import os
from contextlib import AbstractContextManager

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")


class RabbitMQEmitter(AbstractContextManager):
    """Simple wrapper around pika for publishing events."""

    def __init__(self) -> None:
        params = pika.URLParameters(RABBITMQ_URL)
        try:
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
        except Exception:  # pragma: no cover - connection might fail in tests
            self.connection = None
            self.channel = None

    def publish(self, routing_key: str, message: dict) -> None:
        if self.channel:
            self.channel.basic_publish(
                exchange="",
                routing_key=routing_key,
                body=json.dumps(message).encode(),
            )

    def close(self) -> None:
        if self.connection and self.connection.is_open:
            self.connection.close()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
