"""Event log — store and query system events."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Event:
    id: str
    message: str
    level: EventLevel
    timestamp: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class EventLog:
    """Store and query system events."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._events: list[Event] = []

    def log(self, message: str, level: EventLevel = EventLevel.INFO,
            source: str = "", metadata: dict[str, Any] | None = None) -> Event:
        event = Event(
            id=str(uuid.uuid4()),
            message=message,
            level=level,
            timestamp=time.time(),
            source=source,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def info(self, message: str, source: str = "") -> Event:
        return self.log(message, EventLevel.INFO, source)

    def success(self, message: str, source: str = "") -> Event:
        return self.log(message, EventLevel.SUCCESS, source)

    def warning(self, message: str, source: str = "") -> Event:
        return self.log(message, EventLevel.WARNING, source)

    def error(self, message: str, source: str = "") -> Event:
        return self.log(message, EventLevel.ERROR, source)

    def get_all(self) -> list[Event]:
        return list(self._events)

    def get_by_level(self, level: EventLevel) -> list[Event]:
        return [e for e in self._events if e.level == level]

    def get_by_source(self, source: str) -> list[Event]:
        return [e for e in self._events if e.source == source]

    def get_recent(self, count: int = 50) -> list[Event]:
        return self._events[-count:]

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()

    def get_state(self) -> dict[str, Any]:
        return {
            "total": self.count(),
            "info": len(self.get_by_level(EventLevel.INFO)),
            "success": len(self.get_by_level(EventLevel.SUCCESS)),
            "warning": len(self.get_by_level(EventLevel.WARNING)),
            "error": len(self.get_by_level(EventLevel.ERROR)),
        }
