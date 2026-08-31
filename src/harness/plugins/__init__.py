"""Plugin/Hook System — lifecycle hooks, plugin base class."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..errors import PluginError

logger = logging.getLogger(__name__)

HookFunc = Callable[..., Any]


@dataclass
class Hook:
    """A lifecycle hook."""

    name: str
    func: HookFunc
    priority: int = 0
    plugin_id: str | None = None


class HookRegistry:
    """Registry for lifecycle hooks."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[Hook]] = {}
        self._lock = threading.Lock()

    def register(self, event: str, func: HookFunc, priority: int = 0, plugin_id: str | None = None) -> Hook:
        hook = Hook(name=event, func=func, priority=priority, plugin_id=plugin_id)
        with self._lock:
            if event not in self._hooks:
                self._hooks[event] = []
            self._hooks[event].append(hook)
            self._hooks[event].sort(key=lambda h: h.priority, reverse=True)
        return hook

    def unregister(self, event: str, func: HookFunc) -> bool:
        with self._lock:
            if event in self._hooks:
                original = len(self._hooks[event])
                self._hooks[event] = [h for h in self._hooks[event] if h.func != func]
                return len(self._hooks[event]) < original
        return False

    def fire(self, event: str, **kwargs: Any) -> list[Any]:
        hooks = self._hooks.get(event, [])
        results = []
        for hook in hooks:
            try:
                result = hook.func(**kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {event} (plugin={hook.plugin_id}) error: {e}")
                if hook.plugin_id:
                    raise PluginError(f"Hook {event} failed: {e}", plugin_id=hook.plugin_id) from e
                raise
        return results

    def clear_event(self, event: str) -> None:
        with self._lock:
            self._hooks.pop(event, None)

    def clear_all(self) -> None:
        with self._lock:
            self._hooks.clear()

    @property
    def events(self) -> list[str]:
        return list(self._hooks.keys())


@dataclass
class LifecycleHooks:
    """Standard lifecycle events."""

    ON_LOAD = "on_load"
    ON_INIT = "on_init"
    ON_START = "on_start"
    ON_STOP = "on_stop"
    ON_ERROR = "on_error"
    ON_PAUSE = "on_pause"
    ON_RESUME = "on_resume"
    ON_NODE_START = "on_node_start"
    ON_NODE_END = "on_node_end"
    ON_GRAPH_START = "on_graph_start"
    ON_GRAPH_END = "on_graph_end"
    ON_EVAL_START = "on_eval_start"
    ON_EVAL_END = "on_eval_end"
    ON_CRITIQUE = "on_critique"
    ON_FEEDBACK = "on_feedback"
    ON_MEMORY_STORE = "on_memory_store"
    ON_MEMORY_RECALL = "on_memory_recall"
    ON_TOOL_CALL = "on_tool_call"
    ON_TOOL_RESULT = "on_tool_result"


class PluginBase:
    """Base class for plugins with lifecycle hook support."""

    def __init__(self, plugin_id: str, name: str, version: str = "0.1.0") -> None:
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self._hooks = HookRegistry()
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        pass

    def on_init(self) -> None:
        """Called when plugin is initialized."""
        pass

    def on_start(self) -> None:
        """Called when plugin starts."""
        self._active = True

    def on_stop(self) -> None:
        """Called when plugin stops."""
        self._active = False

    def register_hook(self, event: str, func: HookFunc, priority: int = 0) -> Hook:
        return self._hooks.register(event, func, priority, plugin_id=self.plugin_id)

    def fire_hook(self, event: str, **kwargs: Any) -> list[Any]:
        return self._hooks.fire(event, **kwargs)

    def get_info(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "active": self._active,
            "hooks": self._hooks.events,
        }


class PluginManager:
    """Manage plugin lifecycle and hooks."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginBase] = {}
        self._global_hooks = HookRegistry()
        self._lock = threading.Lock()

    def register(self, plugin: PluginBase) -> None:
        with self._lock:
            if plugin.plugin_id in self._plugins:
                logger.warning(f"Plugin {plugin.plugin_id} already registered, overwriting")
            self._plugins[plugin.plugin_id] = plugin
            plugin.on_load()
            plugin.on_init()
        logger.info(f"Registered plugin: {plugin.plugin_id}")

    def start(self, plugin_id: str) -> None:
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.on_start()

    def stop(self, plugin_id: str) -> None:
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.on_stop()

    def get(self, plugin_id: str) -> PluginBase | None:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [p.get_info() for p in self._plugins.values()]

    def fire_global(self, event: str, **kwargs: Any) -> list[Any]:
        return self._global_hooks.fire(event, **kwargs)

    def register_global_hook(self, event: str, func: HookFunc, priority: int = 0) -> Hook:
        return self._global_hooks.register(event, func, priority)

    def unregister(self, plugin_id: str) -> PluginBase | None:
        with self._lock:
            return self._plugins.pop(plugin_id, None)
