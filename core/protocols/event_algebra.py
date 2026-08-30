"""
Action Algebra — Composable action primitives and event algebra.

Action types: READ, CREATE, UPDATE, DELETE, MOVE, COPY, SEND, EXECUTE,
              APPROVE, REJECT, SEARCH, TRANSFORM, OBSERVE, WAIT, SUBSCRIBE

Event types: CREATED, UPDATED, DELETED, FAILED, COMPLETED, EXPIRED,
             CHANGED, ALERT, APPROVAL_REQUIRED, RESOURCE_UNAVAILABLE
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    FAILED = "failed"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CHANGED = "changed"
    ALERT = "alert"
    APPROVAL_REQUIRED = "approval_required"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    STATE_TRANSITION = "state_transition"
    ANOMALY_DETECTED = "anomaly_detected"


class ActionType(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    SEND = "send"
    EXECUTE = "execute"
    APPROVE = "approve"
    REJECT = "reject"
    SEARCH = "search"
    TRANSFORM = "transform"
    OBSERVE = "observe"
    WAIT = "wait"
    SUBSCRIBE = "subscribe"


@dataclass
class Event:
    id: str
    type: EventType
    source: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)
    affected_resources: List[str] = field(default_factory=list)
    processed: bool = False
    subscribers_notified: List[str] = field(default_factory=list)


@dataclass
class EventSubscription:
    subscriber_id: str
    event_filter: Dict[str, Any]  # e.g., {"type": "deployed", "source": "ci"}
    callback: Any = None
    created_at: float = field(default_factory=time.time)


class EventBus:
    """
    Event-driven environment intelligence.
    
    Events → update world state → identify affected missions → recalculate plan
    
    Supports subscription-based agents that react to specific events.
    """

    def __init__(self):
        self.events: List[Event] = []
        self.subscriptions: List[EventSubscription] = []
        self._handlers: Dict[EventType, List[Callable]] = {}

    def subscribe(self, subscriber_id: str, event_filter: Dict[str, Any],
                  callback: Callable = None) -> EventSubscription:
        sub = EventSubscription(
            subscriber_id=subscriber_id,
            event_filter=event_filter,
            callback=callback,
        )
        self.subscriptions.append(sub)
        return sub

    def unsubscribe(self, subscriber_id: str):
        self.subscriptions = [s for s in self.subscriptions if s.subscriber_id != subscriber_id]

    def emit(self, type: EventType, source: str, payload: Dict[str, Any],
             affected_resources: List[str] = None) -> List[str]:
        """Emit a event and notify matching subscribers. Returns list of notified subscriber IDs."""
        event = Event(
            id=str(uuid.uuid4()),
            type=type,
            source=source,
            timestamp=time.time(),
            payload=payload,
            affected_resources=affected_resources or [],
        )
        self.events.append(event)
        
        # Notify subscribers
        notified = []
        for sub in self.subscriptions:
            if self._matches_filter(event, sub.event_filter):
                event.subscribers_notified.append(sub.subscriber_id)
                notified.append(sub.subscriber_id)
                if sub.callback:
                    try:
                        sub.callback(event)
                    except Exception:
                        pass
        
        return notified

    def _matches_filter(self, event: Event, filter: Dict[str, Any]) -> bool:
        for key, value in filter.items():
            if key == "type":
                if isinstance(value, list):
                    if event.type.value not in value:
                        return False
                elif event.type.value != value:
                    return False
            elif key == "source":
                if event.source != value:
                    return False
            elif key == "resource":
                if isinstance(value, list):
                    if not any(r in event.affected_resources for r in value):
                        return False
                elif value not in event.affected_resources:
                    return False
        return True

    def get_events(self, limit: int = 50, event_type: EventType = None,
                   source: str = None, resource: str = None) -> List[Event]:
        events = self.events
        if event_type:
            events = [e for e in events if e.type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        if resource:
            events = [e for e in events if resource in e.affected_resources]
        return events[-limit:]

    def get_state(self) -> Dict[str, Any]:
        return {
            "total_events": len(self.events),
            "subscriptions": len(self.subscriptions),
            "unprocessed": len([e for e in self.events if not e.processed]),
        }
