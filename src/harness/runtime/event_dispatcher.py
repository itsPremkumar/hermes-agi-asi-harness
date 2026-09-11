"""
EventDispatcher - Event-driven architecture for all hooks.

Provides a centralized event system that supports:
- Register/unregister handlers for events
- Priority-based handler ordering (higher priority runs first)
- One-shot handlers
- Event filtering
- Event history
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class Event:
    """Represents a dispatched event."""
    name: str
    data: Any = None
    source: Optional[str] = None
    cancelled: bool = False

    def cancel(self) -> None:
        """Cancel the event to stop further processing."""
        self.cancelled = True


@dataclass(order=True)
class HandlerEntry:
    """An event handler with priority (higher priority = executes first)."""
    priority: int
    handler: Callable = field(compare=False)
    once: bool = field(default=False, compare=False)
    filter_fn: Optional[Callable[[Event], bool]] = field(default=None, compare=False)


class EventDispatcher:
    """Central event dispatcher for hook-based architecture."""

    def __init__(self, max_history: int = 1000):
        self._handlers: Dict[str, List[HandlerEntry]] = defaultdict(list)
        self._global_handlers: List[HandlerEntry] = []
        self._history: List[Event] = []
        self._max_history = max_history
        self._lock = threading.RLock()

    def on(
        self,
        event_name: str,
        handler: Callable[[Event], Any],
        priority: int = 0,
        filter_fn: Optional[Callable[[Event], bool]] = None,
    ) -> Callable[[Event], Any]:
        """Register an event handler."""
        with self._lock:
            entry = HandlerEntry(
                priority=priority, handler=handler, filter_fn=filter_fn
            )
            self._handlers[event_name].append(entry)
            self._handlers[event_name].sort(reverse=True)
        return handler

    def on_decorator(
        self,
        event_name: str,
        priority: int = 0,
        filter_fn: Optional[Callable[[Event], bool]] = None,
    ) -> Callable[[Callable[[Event], Any]], Callable[[Event], Any]]:
        """Return a decorator that registers the handler."""
        def decorator(fn: Callable[[Event], Any]) -> Callable[[Event], Any]:
            self.on(event_name, fn, priority=priority, filter_fn=filter_fn)
            return fn
        return decorator

    def once(
        self,
        event_name: str,
        handler: Callable[[Event], Any],
        priority: int = 0,
    ) -> Callable[[Event], Any]:
        """Register a one-time event handler."""
        with self._lock:
            entry = HandlerEntry(priority=priority, handler=handler, once=True)
            self._handlers[event_name].append(entry)
            self._handlers[event_name].sort(reverse=True)
        return handler

    def on_any(
        self,
        handler: Callable[[Event], Any],
        priority: int = 0,
    ) -> Callable[[Event], Any]:
        """Register a handler for all events."""
        with self._lock:
            entry = HandlerEntry(priority=priority, handler=handler)
            self._global_handlers.append(entry)
            self._global_handlers.sort(reverse=True)
        return handler

    def off(
        self,
        event_name: str,
        handler: Optional[Callable[[Event], Any]] = None,
    ) -> bool:
        """Unregister an event handler. If handler is None, remove all for event."""
        with self._lock:
            if event_name not in self._handlers:
                return False
            if handler is None:
                del self._handlers[event_name]
                return True
            handlers = self._handlers[event_name]
            original_len = len(handlers)
            self._handlers[event_name] = [
                e for e in handlers if e.handler is not handler
            ]
            return len(self._handlers[event_name]) < original_len

    def dispatch(
        self,
        event_name: str,
        data: Any = None,
        source: Optional[str] = None,
    ) -> Event:
        """Dispatch an event to all registered handlers."""
        event = Event(name=event_name, data=data, source=source)

        with self._lock:
            # Record in history
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

            # Get handlers (copy to avoid modification during iteration)
            specific_handlers = list(self._handlers.get(event_name, []))
            global_handlers = list(self._global_handlers)

        # Execute specific handlers
        handlers_to_remove = []
        for entry in specific_handlers:
            if entry.filter_fn and not entry.filter_fn(event):
                continue
            if event.cancelled:
                break
            try:
                entry.handler(event)
            except Exception:
                pass  # Handlers should not break the dispatcher
            if entry.once:
                handlers_to_remove.append((event_name, entry))

        # Execute global handlers
        if not event.cancelled:
            for entry in global_handlers:
                try:
                    entry.handler(event)
                except Exception:
                    pass

        # Clean up one-shot handlers
        if handlers_to_remove:
            with self._lock:
                for name, entry in handlers_to_remove:
                    if name in self._handlers:
                        self._handlers[name] = [
                            e for e in self._handlers[name] if e is not entry
                        ]

        return event

    def has_handlers(self, event_name: str) -> bool:
        """Check if an event has any registered handlers."""
        with self._lock:
            return event_name in self._handlers and len(self._handlers[event_name]) > 0

    def get_handler_count(self, event_name: Optional[str] = None) -> int:
        """Get the number of registered handlers."""
        with self._lock:
            if event_name:
                return len(self._handlers.get(event_name, []))
            return sum(len(h) for h in self._handlers.values()) + len(
                self._global_handlers
            )

    def get_event_names(self) -> Set[str]:
        """Get all event names with registered handlers."""
        with self._lock:
            return set(self._handlers.keys())

    def get_history(
        self, event_name: Optional[str] = None, limit: int = 100
    ) -> List[Event]:
        """Get event history, optionally filtered by name."""
        with self._lock:
            events = self._history
            if event_name:
                events = [e for e in events if e.name == event_name]
            return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        with self._lock:
            self._history.clear()

    def remove_all_listeners(self, event_name: Optional[str] = None) -> None:
        """Remove all listeners for an event, or all events if None."""
        with self._lock:
            if event_name:
                self._handlers.pop(event_name, None)
            else:
                self._handlers.clear()
                self._global_handlers.clear()
