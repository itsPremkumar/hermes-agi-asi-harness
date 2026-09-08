#!/usr/bin/env python3
"""
event_bus.py — High-Performance Typed Async Event Bus for Hermes Kernel
Supports topic pattern subscription, event replay, and decoupled hook dispatching.
"""

import time
import fnmatch
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field

@dataclass
class Event:
    topic: str
    payload: Dict[str, Any]
    sender: str = "kernel"
    timestamp: float = field(default_factory=time.time)
    event_id: Optional[str] = None

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = f"evt_{int(self.timestamp * 1000)}_{abs(hash(self.topic)) % 10000}"

class EventBus:
    def __init__(self, max_history: int = 1000):
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._history: List[Event] = []
        self._max_history = max_history

    def subscribe(self, topic_pattern: str, handler: Callable[[Event], None]):
        """Subscribes a callback to a topic or glob pattern (e.g. 'tool.*', 'agent.step')."""
        if topic_pattern not in self._subscribers:
            self._subscribers[topic_pattern] = []
        if handler not in self._subscribers[topic_pattern]:
            self._subscribers[topic_pattern].append(handler)

    def unsubscribe(self, topic_pattern: str, handler: Callable[[Event], None]):
        """Removes a subscribed handler."""
        if topic_pattern in self._subscribers and handler in self._subscribers[topic_pattern]:
            self._subscribers[topic_pattern].remove(handler)

    def publish(self, event: Event):
        """Publishes an event to all matching subscribers and stores in event history."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        for pattern, handlers in list(self._subscribers.items()):
            if fnmatch.fnmatch(event.topic, pattern):
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        print(f"[EVENT_BUS_ERROR] Error in handler {handler} for {event.topic}: {e}")

    def emit(self, topic: str, payload: Optional[Dict[str, Any]] = None, sender: str = "kernel") -> Event:
        """Convenience method to create and publish an event in one call."""
        evt = Event(topic=topic, payload=payload or {}, sender=sender)
        self.publish(evt)
        return evt

    def get_history(self, topic_pattern: Optional[str] = None, limit: Optional[int] = None) -> List[Event]:
        """Queries recorded event history with optional topic pattern filter."""
        events = self._history
        if topic_pattern:
            events = [e for e in events if fnmatch.fnmatch(e.topic, topic_pattern)]
        if limit:
            events = events[-limit:]
        return events

    def clear(self):
        """Clears subscribers and event history."""
        self._subscribers.clear()
        self._history.clear()
