"""Tests for AgentOS inter-agent communication bus."""

from __future__ import annotations

import asyncio

import pytest

from agentos.bus import Bus, BusError, Message


class TestMessage:
    def test_create_message(self) -> None:
        msg = Message(topic="test", payload="data")
        assert msg.topic == "test"
        assert msg.payload == "data"
        assert msg.message_id is not None

    def test_serialize_deserialize(self) -> None:
        msg = Message(topic="test", payload={"key": "value"}, sender="agent1")
        json_str = msg.to_json()
        restored = Message.from_json(json_str)
        assert restored.topic == msg.topic
        assert restored.payload == msg.payload
        assert restored.sender == msg.sender

    def test_message_with_headers(self) -> None:
        msg = Message(topic="test", payload="data", headers={"rpc": "true"})
        assert msg.headers["rpc"] == "true"


class TestBus:
    def test_publish_subscribe(self) -> None:
        bus = Bus()
        received: list[Message] = []
        bus.subscribe("test.topic", lambda m: received.append(m))
        bus.publish(Message(topic="test.topic", payload="hello"))
        assert len(received) == 1
        assert received[0].payload == "hello"

    def test_multiple_subscribers(self) -> None:
        bus = Bus()
        count = [0]

        def callback(m: Message) -> None:
            count[0] += 1

        bus.subscribe("topic", callback)
        bus.subscribe("topic", callback)
        bus.publish(Message(topic="topic", payload="data"))
        assert count[0] == 2

    def test_no_subscribers(self) -> None:
        bus = Bus()
        delivered = bus.publish(Message(topic="empty", payload="data"))
        assert delivered == 0

    def test_history(self) -> None:
        bus = Bus()
        bus.publish(Message(topic="t1", payload="a"))
        bus.publish(Message(topic="t2", payload="b"))
        history = bus.get_history(limit=10)
        assert len(history) == 2

    def test_history_by_topic(self) -> None:
        bus = Bus()
        bus.publish(Message(topic="t1", payload="a"))
        bus.publish(Message(topic="t2", payload="b"))
        history = bus.get_history(topic="t1")
        assert len(history) == 1
        assert history[0].topic == "t1"

    def test_topics_list(self) -> None:
        bus = Bus()
        bus.subscribe("topic1", lambda m: None)
        bus.subscribe("topic2", lambda m: None)
        assert sorted(bus.topics()) == ["topic1", "topic2"]

    def test_subscriber_count(self) -> None:
        bus = Bus()
        bus.subscribe("topic", lambda m: None)
        bus.subscribe("topic", lambda m: None)
        assert bus.subscriber_count("topic") == 2

    def test_unsubscribe(self) -> None:
        bus = Bus()
        sub_id = bus.subscribe("topic", lambda m: None)
        assert bus.unsubscribe("topic", sub_id) is True

    def test_publish_returns_delivery_count(self) -> None:
        bus = Bus()
        bus.subscribe("topic", lambda m: None)
        bus.subscribe("topic", lambda m: None)
        bus.subscribe("topic", lambda m: None)
        count = bus.publish(Message(topic="topic", payload="data"))
        assert count == 3

    def test_async_publish(self) -> None:
        bus = Bus()
        received: list[Message] = []

        async def handler(m: Message) -> None:
            received.append(m)

        bus.subscribe_async("async.topic", handler)

        async def run() -> None:
            await bus.publish_async(Message(topic="async.topic", payload="data"))

        asyncio.run(run())
        assert len(received) == 1

    def test_rpc_call_timeout(self) -> None:
        bus = Bus()

        async def run() -> None:
            with pytest.raises(BusError, match="timed out"):
                await bus.rpc_call("no_handler", "data", timeout=0.1)

        asyncio.run(run())

    def test_rpc_call_success(self) -> None:
        bus = Bus()

        def handler(m: Message) -> None:
            bus.rpc_respond(m, "response_data")

        bus.subscribe("rpc.topic", handler)

        async def run() -> None:
            response = await bus.rpc_call("rpc.topic", "request", timeout=1.0)
            assert response.payload == "response_data"

        asyncio.run(run())
