"""
Event-Sourced State Store — Section 80 of v7 spec

Current state alone is insufficient for complex debugging.
Event log enables: replay, causal debugging, mission reconstruction,
evolution analysis, counterfactual evaluation, auditing.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """An immutable event in the system."""
    event_type: str
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = "system"
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
        }


class EventStore:
    """Event-sourced state store with replay and reduction."""

    def __init__(self, state_dir: str = None):
        self._events: List[Event] = []
        self._state: Dict[str, Any] = {}
        self._reducers: Dict[str, Callable] = {}
        self._state_dir = Path(state_dir) if state_dir else Path("state/events")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._event_log_file = self._state_dir / "event_log.jsonl"

    def register_reducer(self, event_type: str, reducer: Callable):
        """Register a reducer function for an event type."""
        self._reducers[event_type] = reducer

    def emit(self, event_type: str, data: Dict[str, Any], **kwargs) -> Event:
        """Emit an event and apply its reducer."""
        event = Event(event_type=event_type, data=data, **kwargs)
        self._events.append(event)
        
        # Apply reducer if registered
        if event_type in self._reducers:
            try:
                self._state = self._reducers[event_type](self._state, event)
            except Exception as e:
                logger.error(f"Reducer error for {event_type}: {e}")
        
        # Persist to disk
        self._persist_event(event)
        
        return event

    def _persist_event(self, event: Event):
        """Append event to persistent log."""
        try:
            with open(self._event_log_file, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist event: {e}")

    def get_events(
        self,
        event_type: str = None,
        mission_id: str = None,
        task_id: str = None,
        since: float = None,
        limit: int = 100,
    ) -> List[Event]:
        """Query events with filters."""
        results = self._events
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if mission_id:
            results = [e for e in results if e.mission_id == mission_id]
        if task_id:
            results = [e for e in results if e.task_id == task_id]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[-limit:]

    def replay(self, event_type: str = None, mission_id: str = None) -> List[Event]:
        """Replay events (optionally filtered)."""
        return self.get_events(event_type=event_type, mission_id=mission_id, limit=10000)

    def get_state(self) -> Dict[str, Any]:
        """Get current reduced state."""
        return dict(self._state)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_events": len(self._events),
            "state_keys": len(self._state),
            "registered_reducers": len(self._reducers),
            "log_file": str(self._event_log_file),
        }


class EventSourcedStatePlugin:
    """Plugin wrapper for event store."""

    def __init__(self):
        self.store = EventStore()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.store.get_stats()}

    async def emit(self, event_type: str, data: Dict[str, Any], **kwargs):
        return self.store.emit(event_type, data, **kwargs)


async def create(kernel=None):
    plugin = EventSourcedStatePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
