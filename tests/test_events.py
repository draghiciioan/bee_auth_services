import asyncio
import json
from unittest.mock import AsyncMock, patch

import aio_pika

from events.rabbitmq import emit_event


def test_emit_event_publishes_message():
    connection = AsyncMock()
    connection.__aenter__.return_value = connection
    channel = AsyncMock()
    exchange = AsyncMock()
    connection.channel.return_value = channel
    channel.declare_exchange.return_value = exchange

    with patch("aio_pika.connect_robust", return_value=connection) as connect_mock:
        asyncio.run(emit_event("user.test", {"k": "v"}))
        connect_mock.assert_awaited()
        connection.channel.assert_awaited_once()
        channel.declare_exchange.assert_awaited_once_with(
            "bee.auth.events", aio_pika.ExchangeType.TOPIC
        )
        exchange.publish.assert_awaited_once()
        args, kwargs = exchange.publish.call_args
        assert json.loads(args[0].body.decode()) == {"k": "v"}
        assert kwargs["routing_key"] == "user.test"
