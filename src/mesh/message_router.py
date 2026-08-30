"""Message Router — route messages between nodes in the mesh."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    BROADCAST = "broadcast"
    DIRECT = "direct"
    MULTICAST = "multicast"


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Message:
    id: str
    source: str
    target: str | None  # None for broadcast
    content: str
    msg_type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)


class MessageRouter:
    """Route messages between nodes."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._messages: list[Message] = []
        self._handlers: dict[str, callable] = {}

    def send(self, source: str, target: str | None, content: str,
             msg_type: MessageType = MessageType.DIRECT,
             priority: MessagePriority = MessagePriority.NORMAL) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            source=source,
            target=target,
            content=content,
            msg_type=msg_type,
            priority=priority,
        )
        self._messages.append(msg)
        return msg

    def broadcast(self, source: str, content: str) -> Message:
        return self.send(source, None, content, MessageType.BROADCAST)

    def get_messages(self, node_id: str | None = None) -> list[Message]:
        if node_id is None:
            return list(self._messages)
        return [m for m in self._messages if m.source == node_id or m.target is None or m.target == node_id]

    def get_by_priority(self, priority: MessagePriority) -> list[Message]:
        return [m for m in self._messages if m.priority == priority]

    def count(self) -> int:
        return len(self._messages)

    def clear(self) -> None:
        self._messages.clear()
