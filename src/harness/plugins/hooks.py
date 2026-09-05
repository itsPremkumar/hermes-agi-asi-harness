"""
Hook Registry with priority-ordered event handling.

Provides a centralized registry for lifecycle hooks that plugins
can register. Hooks are called in priority order and can modify
or intercept events.
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


class Priority(enum.IntEnum):
    """Hook priority levels (lower = higher priority)."""
    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


# Lifecycle hook events
HOOK_EVENTS = {
    "on_before_execute",
    "on_after_execute",
    "on_error",
    "on_feedback",
    "on_node_start",
    "on_node_end",
    "on_plugin_load",
    "on_plugin_unload",
    "on_config_reload",
}


@dataclass
class HookEvent:
    """An event that triggers hooks."""
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    cancelled: bool = False

    def cancel(self) -> None:
        """Cancel the event, preventing further processing."""
        self.cancelled = True


# Type alias for hook handlers
HookHandler = Callable[[HookEvent], Awaitable[None]]


@dataclass
class HookRegistration:
    """A registered hook with metadata."""
    handler: HookHandler
    priority: int
    plugin_id: str
    hook_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    once: bool = False
    active: bool = True


class HookRegistry:
    """Central registry for lifecycle hooks.
    
    Plugins register hooks for specific events. When an event fires,
    all registered handlers are called in priority order. Handlers
    can cancel events to prevent further processing.
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[HookRegistration]] = {}
        self._history: list[tuple[str, str, float]] = []  # (event, hook_id, duration)

    def register(
        self,
        event: str,
        handler: HookHandler,
        priority: int = Priority.NORMAL,
        plugin_id: str = "",
        once: bool = False,
    ) -> str:
        """Register a hook handler for an event.
        
        Args:
            event: The event name to hook into.
            handler: Async callable that receives the HookEvent.
            priority: Priority level (lower = called first).
            plugin_id: ID of the plugin registering the hook.
            once: If True, the hook is removed after first call.
            
        Returns:
            The hook registration ID.
            
        Raises:
            ValueError: If the event name is not recognized.
        """
        if event not in HOOK_EVENTS:
            raise ValueError(
                f"Unknown hook event: {event!r}. "
                f"Valid events: {sorted(HOOK_EVENTS)}"
            )
        
        if event not in self._hooks:
            self._hooks[event] = []
        
        registration = HookRegistration(
            handler=handler,
            priority=priority,
            plugin_id=plugin_id,
            once=once,
        )
        self._hooks[event].append(registration)
        # Keep sorted by priority
        self._hooks[event].sort(key=lambda r: r.priority)
        
        logger.debug(
            "Registered hook %s for event %s (priority=%d, plugin=%s)",
            registration.hook_id, event, priority, plugin_id,
        )
        return registration.hook_id

    def unregister(self, hook_id: str) -> bool:
        """Unregister a hook by its ID.
        
        Args:
            hook_id: The hook registration ID.
            
        Returns:
            True if the hook was found and removed.
        """
        for event, registrations in self._hooks.items():
            for i, reg in enumerate(registrations):
                if reg.hook_id == hook_id:
                    registrations.pop(i)
                    logger.debug("Unregistered hook %s from event %s", hook_id, event)
                    return True
        return False

    def unregister_all(self, plugin_id: str) -> int:
        """Unregister all hooks for a plugin.
        
        Args:
            plugin_id: The plugin ID.
            
        Returns:
            Number of hooks removed.
        """
        count = 0
        for event, registrations in self._hooks.items():
            to_remove = [r for r in registrations if r.plugin_id == plugin_id]
            for reg in to_remove:
                registrations.remove(reg)
                count += 1
        if count:
            logger.debug("Unregistered %d hooks for plugin %s", count, plugin_id)
        return count

    def get_hooks(self, event: str) -> list[HookRegistration]:
        """Get all registered hooks for an event."""
        return list(self._hooks.get(event, []))

    def get_registered_events(self) -> list[str]:
        """Get all event names with registered hooks."""
        return sorted(
            event for event, hooks in self._hooks.items() if hooks
        )

    async def fire(self, event: str, **data: Any) -> HookEvent:
        """Fire an event, calling all registered hooks.
        
        Args:
            event: The event name.
            **data: Event data passed to handlers.
            
        Returns:
            The HookEvent after all handlers have run.
        """
        hook_event = HookEvent(name=event, data=data)
        registrations = self._hooks.get(event, [])
        
        for reg in registrations:
            if not reg.active:
                continue
            if hook_event.cancelled:
                break
            
            start = time.time()
            try:
                await reg.handler(hook_event)
            except Exception as e:
                logger.exception(
                    "Hook %s for event %s raised an exception: %s",
                    reg.hook_id, event, e,
                )
                # Continue to next hook; don't let one hook break the chain
            finally:
                duration = time.time() - start
                self._history.append((event, reg.hook_id, duration))
            
            if reg.once:
                reg.active = False
        
        return hook_event

    def get_history(
        self, event: Optional[str] = None, limit: int = 100
    ) -> list[tuple[str, str, float]]:
        """Get hook execution history.
        
        Args:
            event: Filter by event name.
            limit: Maximum number of entries.
            
        Returns:
            List of (event, hook_id, duration) tuples.
        """
        history = self._history
        if event:
            history = [h for h in history if h[0] == event]
        return history[-limit:]

    def clear_history(self) -> None:
        """Clear hook execution history."""
        self._history.clear()

    def clear(self) -> None:
        """Clear all registered hooks."""
        self._hooks.clear()
        self._history.clear()

    @property
    def hook_count(self) -> int:
        """Total number of registered hooks."""
        return sum(len(hooks) for hooks in self._hooks.values())

    def __repr__(self) -> str:
        return (
            f"HookRegistry(events={len(self._hooks)}, "
            f"hooks={self.hook_count})"
        )
