"""Tests for MessageRouter."""
from src.mesh.message_router import MessageRouter, MessageType, MessagePriority


class TestMessageRouter:
    def test_create(self):
        mr = MessageRouter()
        assert mr.count() == 0

    def test_send(self):
        mr = MessageRouter()
        msg = mr.send("node1", "node2", "hello")
        assert msg.source == "node1"
        assert msg.target == "node2"
        assert msg.content == "hello"
        assert msg.msg_type == MessageType.DIRECT
        assert mr.count() == 1

    def test_broadcast(self):
        mr = MessageRouter()
        msg = mr.broadcast("node1", "hello all")
        assert msg.target is None
        assert msg.msg_type == MessageType.BROADCAST

    def test_get_messages(self):
        mr = MessageRouter()
        mr.send("node1", "node2", "hello")
        mr.send("node2", "node1", "hi")
        messages = mr.get_messages("node1")
        # get_messages returns messages where node1 is source or target
        assert len(messages) == 2
        sources = {m.source for m in messages}
        assert "node1" in sources
        assert "node2" in sources

    def test_get_by_priority(self):
        mr = MessageRouter()
        mr.send("node1", "node2", "normal")
        mr.send("node1", "node2", "urgent", priority=MessagePriority.HIGH)
        high = mr.get_by_priority(MessagePriority.HIGH)
        assert len(high) == 1

    def test_clear(self):
        mr = MessageRouter()
        mr.send("node1", "node2", "hello")
        mr.clear()
        assert mr.count() == 0
