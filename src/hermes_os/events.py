"""
HERMES INTELLIGENCE OS — PLANE 01: UNIVERSAL INTERACTION & EVENT BUS
====================================================================
Unified event-driven nervous system for all Hermes interactions.
Ingests from CLI, Web, Desktop, API, Scheduled Crons, Webhooks, and Subagents.
Schema-enforced, replayable, and observable.
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.events")


class EventSource(str, Enum):
    CLI = "cli"
    WEB = "web"
    DESKTOP = "desktop"
    API = "api"
    CRON = "cron"
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    SYSTEM = "system"


@dataclass
class HermesEvent:
    """Universal schema for all events flowing through Hermes Intelligence OS."""
    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:10]}")
    event_type: str = "system.heartbeat"
    source: EventSource | str = EventSource.SYSTEM
    identity: str = "anonymous"
    payload: dict[str, Any] = field(default_factory=dict)
    authorization: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    trace_id: str = field(default_factory=lambda: f"trc-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source.value if isinstance(self.source, EventSource) else str(self.source),
            "identity": self.identity,
            "payload": self.payload,
            "authorization": self.authorization,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HermesEvent:
        return cls(
            event_id=data.get("event_id", f"evt-{uuid.uuid4().hex[:10]}"),
            event_type=data.get("event_type", "system.generic"),
            source=data.get("source", EventSource.SYSTEM),
            identity=data.get("identity", "anonymous"),
            payload=data.get("payload", {}),
            authorization=data.get("authorization", {}),
            correlation_id=data.get("correlation_id", ""),
            trace_id=data.get("trace_id", ""),
            timestamp=data.get("timestamp", time.time()),
        )


class UniversalEventBus:
    """
    High-performance asynchronous event bus supporting:
    - Wildcard pattern matching (e.g. 'mission.*', 'tool.*')
    - Synchronous and asynchronous subscriber dispatch
    - Event history buffer and persistent audit logging
    - Replay capabilities for recovery and post-mortems
    """

    def __init__(self, workspace_root: str = ".", max_history: int = 1000):
        self.workspace_root = workspace_root
        self.max_history = max_history
        self._subscribers: dict[str, list[Callable[[HermesEvent], Any]]] = defaultdict(list)
        self._async_subscribers: dict[str, list[Callable[[HermesEvent], Awaitable[Any]]]] = defaultdict(list)
        self._history: list[HermesEvent] = []
        self._event_count: int = 0
        self.log_dir = Path(workspace_root) / ".hermes" / "events"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def subscribe(self, pattern: str, handler: Callable[[HermesEvent], Any]) -> None:
        """Subscribe a synchronous callback to an event pattern."""
        self._subscribers[pattern].append(handler)

    def subscribe_async(self, pattern: str, handler: Callable[[HermesEvent], Awaitable[Any]]) -> None:
        """Subscribe an asynchronous callback to an event pattern."""
        self._async_subscribers[pattern].append(handler)

    def publish(self, event: HermesEvent) -> None:
        """Publish an event to all matching sync subscribers and record to history."""
        self._record_event(event)

        for pattern, handlers in self._subscribers.items():
            if fnmatch.fnmatch(event.event_type, pattern):
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error("Error in sync event subscriber for '%s': %s", event.event_type, e)

    async def publish_async(self, event: HermesEvent) -> None:
        """Publish an event to all matching async & sync subscribers."""
        self.publish(event)

        tasks = []
        for pattern, handlers in self._async_subscribers.items():
            if fnmatch.fnmatch(event.event_type, pattern):
                for handler in handlers:
                    tasks.append(self._invoke_async_safe(handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _invoke_async_safe(self, handler: Callable[[HermesEvent], Awaitable[Any]], event: HermesEvent) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error("Error in async event subscriber for '%s': %s", event.event_type, e)

    def _record_event(self, event: HermesEvent) -> None:
        self._history.append(event)
        self._event_count += 1
        if len(self._history) > self.max_history:
            self._history.pop(0)
        # Persistent JSONL audit log (rotation by size, best-effort, offline-safe)
        try:
            audit = self.log_dir / "audit.jsonl"
            with open(audit, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
            try:
                if audit.stat().st_size > 5_000_000:
                    (self.log_dir / "audit.prev.jsonl").write_bytes(audit.read_bytes()[-2_000_000:])
                    audit.write_text("", encoding="utf-8")
            except Exception:
                pass
        except Exception as e:
            logger.debug("Event audit persist failed: %s", e)

    def get_history(self, filter_type: Optional[str] = None, limit: int = 50) -> list[HermesEvent]:
        """Retrieve recent events matching an optional glob pattern."""
        if not filter_type:
            return self._history[-limit:]
        filtered = [e for e in self._history if fnmatch.fnmatch(e.event_type, filter_type)]
        return filtered[-limit:]

    def replay(self, events: list[HermesEvent]) -> None:
        """Replay a sequence of events through registered subscribers."""
        for ev in events:
            self.publish(ev)

    def stats(self) -> dict[str, Any]:
        return {
            "total_events_published": self._event_count,
            "buffered_history": len(self._history),
            "sync_subscriber_patterns": len(self._subscribers),
            "async_subscriber_patterns": len(self._async_subscribers),
        }
