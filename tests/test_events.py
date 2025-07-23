import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
import aio_pika

from events import rabbitmq


@pytest.fixture(autouse=True)
def reset_state():
    rabbitmq._connection = None
    rabbitmq._channel = None
    rabbitmq._exchange = None
    yield
    rabbitmq._connection = None
    rabbitmq._channel = None
    rabbitmq._exchange = None


def test_emit_event_publishes_message():
    connection = AsyncMock()
    channel = AsyncMock()
    exchange = AsyncMock()
    connection.channel.return_value = channel
    channel.declare_exchange.return_value = exchange
    connection.is_closed = False
    channel.is_closed = False
    exchange.is_closed = False

    with patch("aio_pika.connect_robust", return_value=connection) as connect_mock:
        asyncio.run(rabbitmq.emit_event("user.test", {"k": "v"}))
        connect_mock.assert_awaited_once()
        connection.channel.assert_awaited_once()
        channel.declare_exchange.assert_awaited_once_with(
            "bee.auth.events", aio_pika.ExchangeType.TOPIC
        )
        exchange.publish.assert_awaited_once()
        args, kwargs = exchange.publish.call_args
        assert json.loads(args[0].body.decode()) == {"k": "v"}
        assert kwargs["routing_key"] == "user.test"


def test_connection_is_reused():
    connection = AsyncMock()
    channel = AsyncMock()
    exchange = AsyncMock()
    connection.channel.return_value = channel
    channel.declare_exchange.return_value = exchange
    connection.is_closed = False
    channel.is_closed = False
    exchange.is_closed = False

    with patch("aio_pika.connect_robust", return_value=connection) as connect_mock:
        asyncio.run(rabbitmq.emit_event("user.one", {"a": 1}))
        asyncio.run(rabbitmq.emit_event("user.two", {"b": 2}))
        # connection should be created only once
        connect_mock.assert_awaited_once()
        assert exchange.publish.await_count == 2


def test_emit_event_retries_and_logs():
    connection = AsyncMock()
    channel = AsyncMock()
    exchange = AsyncMock()
    connection.channel.return_value = channel
    channel.declare_exchange.return_value = exchange
    connection.is_closed = False
    channel.is_closed = False
    exchange.is_closed = False
    exchange.publish = AsyncMock(side_effect=[Exception("err1"), Exception("err2"), None])

    logger_mock = Mock()

    with (
        patch("aio_pika.connect_robust", return_value=connection),
        patch("events.rabbitmq.logger", logger_mock),
        patch("events.rabbitmq.asyncio.sleep", new=AsyncMock()),
    ):
        asyncio.run(rabbitmq.emit_event("user.retry", {"k": "v"}, retries=3, delay=0))

    assert exchange.publish.await_count == 3
    assert logger_mock.exception.call_count == 2


def test_emit_event_raises_after_max_retries():
    connection = AsyncMock()
    channel = AsyncMock()
    exchange = AsyncMock()
    connection.channel.return_value = channel
    channel.declare_exchange.return_value = exchange
    connection.is_closed = False
    channel.is_closed = False
    exchange.is_closed = False
    exchange.publish = AsyncMock(side_effect=Exception("err"))

    logger_mock = Mock()

    with (
        patch("aio_pika.connect_robust", return_value=connection),
        patch("events.rabbitmq.logger", logger_mock),
        patch("events.rabbitmq.asyncio.sleep", new=AsyncMock()),
    ):
        with pytest.raises(Exception):
            asyncio.run(rabbitmq.emit_event("user.retry", {"k": "v"}, retries=2, delay=0))

    assert exchange.publish.await_count == 2
    assert logger_mock.exception.call_count == 2
