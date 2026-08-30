"""Lifecycle manager — orchestrate plugin lifecycle transitions."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .plugin_base import Plugin, PluginStatus


class LifecycleEvent(Enum):
    """Lifecycle events."""
    BEFORE_LOAD = "before_load"
    AFTER_LOAD = "after_load"
    BEFORE_INIT = "before_init"
    AFTER_INIT = "after_init"
    BEFORE_PAUSE = "before_pause"
    AFTER_PAUSE = "after_pause"
    BEFORE_RESUME = "before_resume"
    AFTER_RESUME = "after_resume"
    BEFORE_STOP = "before_stop"
    AFTER_STOP = "after_stop"
    ON_ERROR = "on_error"


@dataclass
class LifecycleHook:
    """A hook for a lifecycle event."""
    event: LifecycleEvent
    callback: Callable[[Plugin], None]
    priority: int = 0


class LifecycleManager:
    """Manages plugin lifecycle with hooks and event notifications."""

    def __init__(self):
        self._lock = threading.RLock()
        self._hooks: dict[LifecycleEvent, list[LifecycleHook]] = {}
        self._event_log: list[dict[str, Any]] = []
        self._listeners: list[Callable[[LifecycleEvent, Plugin], None]] = []

    def add_hook(self, hook: LifecycleHook) -> None:
        with self._lock:
            self._hooks.setdefault(hook.event, []).append(hook)
            self._hooks[hook.event].sort(key=lambda h: h.priority)

    def remove_hook(self, event: LifecycleEvent, callback: Callable) -> bool:
        with self._lock:
            hooks = self._hooks.get(event, [])
            for i, hook in enumerate(hooks):
                if hook.callback == callback:
                    hooks.pop(i)
                    return True
            return False

    def add_listener(self, listener: Callable[[LifecycleEvent, Plugin], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> bool:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)
                return True
            return False

    def _fire_event(self, event: LifecycleEvent, plugin: Plugin) -> None:
        with self._lock:
            # Run hooks
            hooks = self._hooks.get(event, [])
            for hook in hooks:
                try:
                    hook.callback(plugin)
                except Exception as e:
                    plugin.record_error(f"Hook error: {e}")

            # Notify listeners
            listeners = list(self._listeners)

            # Log event
            self._event_log.append({
                "event": event.value,
                "plugin_id": plugin.metadata.id,
                "timestamp": time.time(),
            })

        # Call listeners outside lock
        for listener in listeners:
            try:
                listener(event, plugin)
            except Exception:
                pass

    def load(self, plugin: Plugin) -> None:
        self._fire_event(LifecycleEvent.BEFORE_LOAD, plugin)
        plugin.on_load()
        self._fire_event(LifecycleEvent.AFTER_LOAD, plugin)

    def init(self, plugin: Plugin) -> None:
        self._fire_event(LifecycleEvent.BEFORE_INIT, plugin)
        plugin.on_init()
        self._fire_event(LifecycleEvent.AFTER_INIT, plugin)

    def pause(self, plugin: Plugin) -> None:
        self._fire_event(LifecycleEvent.BEFORE_PAUSE, plugin)
        plugin.on_pause()
        self._fire_event(LifecycleEvent.AFTER_PAUSE, plugin)

    def resume(self, plugin: Plugin) -> None:
        self._fire_event(LifecycleEvent.BEFORE_RESUME, plugin)
        plugin.on_resume()
        self._fire_event(LifecycleEvent.AFTER_RESUME, plugin)

    def stop(self, plugin: Plugin) -> None:
        self._fire_event(LifecycleEvent.BEFORE_STOP, plugin)
        plugin.on_stop()
        self._fire_event(LifecycleEvent.AFTER_STOP, plugin)

    def start(self, plugin: Plugin) -> None:
        """Full start: load + init."""
        self.load(plugin)
        if plugin.status != PluginStatus.ERROR:
            self.init(plugin)

    def restart(self, plugin: Plugin) -> None:
        """Stop and start a plugin."""
        if plugin.status == PluginStatus.ACTIVE:
            self.stop(plugin)
        self.start(plugin)

    def get_event_log(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._event_log)

    def clear_log(self) -> None:
        with self._lock:
            self._event_log.clear()
