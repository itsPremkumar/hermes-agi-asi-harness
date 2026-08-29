#!/usr/bin/env python3
"""
Event Bus — typed async event bus with topic patterns and replay.

Every subsystem communicates via events. Plugins subscribe with glob patterns
(e.g. 'tool.*', 'agent.step'). Supports event replay for debugging.

Event types:
  agent.loop_start / agent.step_start / agent.step_end / agent.loop_end
  tool.pre_execute / tool.post_execute
  orchestration.goal_start / orchestration.subtask_start / orchestration.goal_end
  verifier.check / critic.critique
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("hermes.event_bus")


@dataclass
class Event:
    topic: str
    payload: Dict[str, Any]
    sender: str = "kernel"
    timestamp: float = field(default_factory=time.time)
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"evt_{int(self.timestamp * 1000)}_{abs(hash(self.topic)) % 10000}"


Handler = Callable[[Event], Any]


class EventBus:
    """Async event bus with topic patterns and replay history."""

    def __init__(self, max_history: int = 1000):
        self._subscribers: Dict[str, List[Handler]] = {}
        self._history: List[Event] = []
        self._max_history = max_history

    def subscribe(self, topic_pattern: str, handler: Handler):
        """Subscribe a handler to a topic or glob pattern."""
        if topic_pattern not in self._subscribers:
            self._subscribers[topic_pattern] = []
        if handler not in self._subscribers[topic_pattern]:
            self._subscribers[topic_pattern].append(handler)

    def unsubscribe(self, topic_pattern: str, handler: Handler):
        if topic_pattern in self._subscribers and handler in self._subscribers[topic_pattern]:
            self._subscribers[topic_pattern].remove(handler)

    def publish(self, event: Event):
        """Publish an event to all matching subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        for pattern, handlers in list(self._subscribers.items()):
            if fnmatch.fnmatch(event.topic, pattern):
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error("Event handler error for %s: %s", event.topic, e)

    def emit(self, topic: str, payload: Optional[Dict[str, Any]] = None, sender: str = "kernel") -> Event:
        """Convenience: create and publish in one call."""
        evt = Event(topic=topic, payload=payload or {}, sender=sender)
        self.publish(evt)
        return evt

    def replay(self, topic_pattern: str = "*", limit: int = 50) -> List[Event]:
        """Replay events matching a pattern (most recent first)."""
        matching = [e for e in self._history if fnmatch.fnmatch(e.topic, topic_pattern)]
        return matching[-limit:]

    @property
    def history(self) -> List[Event]:
        return list(self._history)
