"""Tests for MessageBus."""
import time

import pytest

from src.harness.runtime.message_bus import MessageBus, Message


class TestMessageBus:
    def test_init(self):
        mb = MessageBus()
        assert len(mb.get_topics()) == 0

    def test_subscribe_publish(self):
        mb = MessageBus()
        results = []
        mb.subscribe("test", lambda msg: results.append(msg.data))
        mb.publish("test", data="hello")
        assert results == ["hello"]

    def test_multiple_subscribers(self):
        mb = MessageBus()
        results_a = []
        results_b = []
        mb.subscribe("test", lambda msg: results_a.append(msg.data))
        mb.subscribe("test", lambda msg: results_b.append(msg.data))
        mb.publish("test", data="msg")
        assert results_a == ["msg"]
        assert results_b == ["msg"]

    def test_unsubscribe_specific(self):
        mb = MessageBus()
        results = []
        handler = lambda msg: results.append(msg.data)
        mb.subscribe("test", handler)
        mb.unsubscribe("test", handler)
        mb.publish("test", data="msg")
        assert results == []

    def test_unsubscribe_all(self):
        mb = MessageBus()
        results = []
        mb.subscribe("test", lambda msg: results.append("a"))
        mb.subscribe("test", lambda msg: results.append("b"))
        mb.unsubscribe("test")
        mb.publish("test")
        assert results == []

    def test_unsubscribe_missing(self):
        mb = MessageBus()
        assert mb.unsubscribe("missing") is False

    def test_pattern_subscribe(self):
        mb = MessageBus()
        results = []
        mb.subscribe_pattern("agent.*", lambda msg: results.append(msg.topic))
        mb.publish("agent.123")
        mb.publish("other.456")
        assert results == ["agent.123"]

    def test_pattern_unsubscribe(self):
        mb = MessageBus()
        results = []
        handler = lambda msg: results.append(msg.topic)
        mb.subscribe_pattern("agent.*", handler)
        mb.unsubscribe_pattern(handler)
        mb.publish("agent.123")
        assert results == []

    def test_message_history(self):
        mb = MessageBus()
        mb.publish("test", data="msg1")
        mb.publish("test", data="msg2")
        history = mb.get_history("test")
        assert len(history) == 2
        assert history[0].data == "msg1"
        assert history[1].data == "msg2"

    def test_history_limit(self):
        mb = MessageBus(max_history_per_topic=3)
        for i in range(5):
            mb.publish("test", data=i)
        history = mb.get_history("test")
        assert len(history) == 3
        assert history[-1].data == 4

    def test_clear_history_specific(self):
        mb = MessageBus()
        mb.publish("test", data="msg")
        mb.clear_history("test")
        assert len(mb.get_history("test")) == 0

    def test_clear_history_all(self):
        mb = MessageBus()
        mb.publish("test1", data="a")
        mb.publish("test2", data="b")
        mb.clear_history()
        assert len(mb.get_history("test1")) == 0
        assert len(mb.get_history("test2")) == 0

    def test_get_topics(self):
        mb = MessageBus()
        mb.subscribe("topic1", lambda msg: None)
        mb.publish("topic2", data="msg")
        topics = mb.get_topics()
        assert "topic1" in topics
        assert "topic2" in topics

    def test_get_subscribers(self):
        mb = MessageBus()
        mb.subscribe("test", lambda msg: None)
        mb.subscribe("test", lambda msg: None)
        assert mb.get_subscribers("test") == 2

    def test_get_subscribers_with_pattern(self):
        mb = MessageBus()
        mb.subscribe_pattern("agent.*", lambda msg: None)
        assert mb.get_subscribers("agent.123") == 1

    def test_message_sender(self):
        mb = MessageBus()
        results = []
        mb.subscribe("test", lambda msg: results.append(msg.sender))
        mb.publish("test", sender="agent-1")
        assert results == ["agent-1"]

    def test_message_timestamp(self):
        mb = MessageBus()
        before = time.time()
        msg = mb.publish("test")
        after = time.time()
        assert before <= msg.timestamp <= after

    def test_message_metadata(self):
        mb = MessageBus()
        results = []
        mb.subscribe("test", lambda msg: results.append(msg.metadata))
        mb.publish("test", metadata={"key": "value"})
        assert results == [{"key": "value"}]

    def test_filter_fn(self):
        mb = MessageBus()
        results = []
        mb.subscribe("test", lambda msg: results.append(msg.data), filter_fn=lambda msg: msg.data > 5)
        mb.publish("test", data=3)
        mb.publish("test", data=10)
        assert results == [10]

    def test_async_publish(self):
        mb = MessageBus()
        results = []
        mb.subscribe("test", lambda msg: results.append(msg.data))
        mb.start_async()
        mb.publish_async("test", data="async_msg")
        time.sleep(0.5)
        mb.stop_async()
        assert "async_msg" in results

    def test_remove_all_subscribers(self):
        mb = MessageBus()
        mb.subscribe("test", lambda msg: None)
        mb.subscribe_pattern("agent.*", lambda msg: None)
        mb.remove_all_subscribers()
        assert mb.get_subscribers("test") == 0

    def test_priority_ordering(self):
        mb = MessageBus()
        results = []
        mb.subscribe("test", lambda msg: results.append("low"), priority=0)
        mb.subscribe("test", lambda msg: results.append("high"), priority=10)
        mb.publish("test")
        assert results == ["high", "low"]

    def test_decorator_usage(self):
        mb = MessageBus()
        results = []
        decorator = mb.subscribe_decorator("test")
        @decorator
        def handler(msg):
            results.append(msg.data)
        mb.publish("test", data="decorated")
        assert results == ["decorated"]
