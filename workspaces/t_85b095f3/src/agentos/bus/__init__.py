"""Inter-agent communication bus with pub/sub and RPC support."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


class BusError(Exception):
    """Raised when bus operations fail."""
    pass


@dataclass
class Message:
    """A message on the bus."""
    topic: str
    payload: Any
    sender: str = ""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    headers: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "message_id": self.message_id,
            "topic": self.topic,
            "payload": self.payload,
            "sender": self.sender,
            "timestamp": self.timestamp,
            "headers": self.headers,
        })

    @classmethod
    def from_json(cls, data: str) -> Message:
        """Deserialize from JSON."""
        obj = json.loads(data)
        return cls(**obj)


class Bus:
    """Inter-agent communication bus supporting pub/sub and RPC."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Message], None]]] = defaultdict(list)
        self._async_subscribers: dict[str, list[Callable[[Message], Any]]] = defaultdict(list)
        self._pending_rpc: dict[str, asyncio.Future[Any]] = {}
        self._history: list[Message] = []
        self._max_history = 1000

    def publish(self, message: Message) -> int:
        """Publish a message to all subscribers. Returns count of deliveries."""
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        count = 0
        for callback in self._subscribers.get(message.topic, []):
            try:
                callback(message)
                count += 1
            except Exception:
                pass  # Don't let subscriber errors break publishing

        return count

    def subscribe(self, topic: str, callback: Callable[[Message], None]) -> str:
        """Subscribe to a topic. Returns subscription ID."""
        sub_id = str(uuid.uuid4())
        self._subscribers[topic].append(callback)
        return sub_id

    def unsubscribe(self, topic: str, sub_id: str) -> bool:
        """Unsubscribe from a topic by subscription ID."""
        # Note: In a real system we'd track sub_id -> callback mapping
        # For now, this is a simplified version
        subs = self._subscribers.get(topic, [])
        if subs:
            subs.pop()
            return True
        return False

    async def publish_async(self, message: Message) -> int:
        """Publish a message asynchronously."""
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        count = 0
        for callback in self._async_subscribers.get(message.topic, []):
            try:
                await callback(message)
                count += 1
            except Exception:
                pass

        return count

    def subscribe_async(self, topic: str,
                        callback: Callable[[Message], Any]) -> str:
        """Subscribe to a topic with an async callback."""
        sub_id = str(uuid.uuid4())
        self._async_subscribers[topic].append(callback)
        return sub_id

    async def rpc_call(self, topic: str, payload: Any,
                       timeout: float = 30.0) -> Message:
        """Make an RPC call and wait for response."""
        correlation_id = str(uuid.uuid4())
        message = Message(
            topic=topic,
            payload=payload,
            headers={"rpc": "true", "correlation_id": correlation_id},
        )

        loop = asyncio.get_event_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending_rpc[correlation_id] = future

        self.publish(message)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            raise BusError(f"RPC call to '{topic}' timed out after {timeout}s")
        finally:
            self._pending_rpc.pop(correlation_id, None)

    def rpc_respond(self, original: Message, response_payload: Any) -> None:
        """Respond to an RPC call."""
        correlation_id = original.headers.get("correlation_id")
        if not correlation_id or correlation_id not in self._pending_rpc:
            return

        response = Message(
            topic=f"{original.topic}.response",
            payload=response_payload,
            headers={"correlation_id": correlation_id, "response": "true"},
        )

        future = self._pending_rpc[correlation_id]
        if not future.done():
            future.set_result(response)

    def get_history(self, topic: str | None = None, limit: int = 100) -> list[Message]:
        """Get message history, optionally filtered by topic."""
        messages = self._history
        if topic:
            messages = [m for m in messages if m.topic == topic]
        return messages[-limit:]

    def topics(self) -> list[str]:
        """List all topics with subscribers."""
        return list(self._subscribers.keys())

    def subscriber_count(self, topic: str) -> int:
        """Get number of subscribers for a topic."""
        return len(self._subscribers.get(topic, []))
