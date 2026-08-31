#!/usr/bin/env python3
"""
Event Bus Plugin — typed async event bus with topic patterns and replay.

The nervous system of the harness. Every subsystem communicates via events.
Supports glob-pattern subscriptions, event replay, and graceful backpressure.

Extracted & enhanced from:
- hermes-asi-master: core/events/event_bus.py
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.event_bus")


@dataclass
class Event:
    """A single event on the bus."""
    topic: str
    payload: dict = field(default_factory=dict)
    sender: str = "kernel"
    timestamp: float = field(default_factory=time.time)
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"evt_{int(self.timestamp * 1e6)}"


Handler = Callable[[Event], Any]


class EventBus:
    """Async event bus with topic-pattern subscriptions and replay."""

    def __init__(self, max_history: int = 5000):
        self._subscribers: dict = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = max_history
        self._started = False

    async def start(self) -> bool:
        """Start the event bus."""
        self._started = True
        logger.info("EventBus started")
        return True

    async def stop(self) -> bool:
        """Stop the event bus."""
        self._started = False
        logger.info("EventBus stopped")
        return True

    def subscribe(self, topic_pattern: str, handler: Handler):
        """Subscribe a handler to a topic or glob pattern."""
        self._subscribers[topic_pattern].append(handler)

    def unsubscribe(self, topic_pattern: str, handler: Handler):
        if handler in self._subscribers.get(topic_pattern, []):
            self._subscribers[topic_pattern].remove(handler)

    def publish(self, event: Event):
        """Publish an event synchronously to all matching subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        for pattern, handlers in list(self._subscribers.items()):
            if fnmatch.fnmatch(event.topic, pattern) or pattern == "*":
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error("Event handler error (%s <- %s): %s", pattern, event.topic, e)

    def emit(self, topic: str, payload: dict | None = None, sender: str = "kernel") -> Event:
        """Convenience: create and publish in one call."""
        evt = Event(topic=topic, payload=payload or {}, sender=sender)
        self.publish(evt)
        return evt

    async def emit_async(self, topic: str, payload: dict | None = None, sender: str = "kernel") -> Event:
        """Async-safe emit."""
        return self.emit(topic, payload, sender)

    def replay(self, topic_pattern: str = "*", limit: int = 100) -> list[Event]:
        """Replay events matching a pattern (most recent first)."""
        matching = [e for e in reversed(self._history) if fnmatch.fnmatch(e.topic, topic_pattern)]
        return matching[:limit]

    @property
    def history(self) -> list[Event]:
        return list(self._history)

    def get_subscriber_count(self, topic: str | None = None) -> int:
        if topic:
            total = 0
            for pattern, handlers in self._subscribers.items():
                if fnmatch.fnmatch(topic, pattern) or pattern == "*":
                    total += len(handlers)
            return total
        return sum(len(h) for h in self._subscribers.values())

    async def health(self) -> dict:
        return {
            "status": "healthy" if self._started else "degraded",
            "type": "event_bus",
            "events_stored": len(self._history),
            "subscribers": sum(len(h) for h in self._subscribers.values()),
            "topics": list(self._subscribers.keys()),
        }

    def get_capabilities(self) -> list[str]:
        return ["event.publish", "event.subscribe", "event.replay"]


# Singleton instance
_instance: EventBus | None = None


async def create(kernel: Any) -> EventBus:
    """Kernel factory: create and return the EventBus plugin."""
    global _instance
    if _instance is None:
        _instance = EventBus()
    await _instance.start()
    return _instance
