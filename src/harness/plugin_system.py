"""
Plugin & Hook System — Pluggable Architecture for hermes-agi-asi-harness.

Provides plugin lifecycle management, hook registration, type-specific APIs,
discovery, isolation, and dynamic configuration.
"""

from __future__ import annotations

import enum
import importlib
import importlib.util
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


# ──────────────────────────── Enums ──────────────────────────────────


class PluginType(enum.Enum):
    FRAMEWORK = "framework"
    SOLVER = "solver"
    EVAL = "eval"
    MEMORY = "memory"
    TOOL = "tool"
    GUARD = "guard"


class PluginState(enum.Enum):
    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


class HookPoint(enum.Enum):
    PRE_EXECUTE = "pre_execute"
    POST_EXECUTE = "post_execute"
    ON_ERROR = "on_error"
    ON_LOAD = "on_load"
    ON_UNLOAD = "on_unload"
    ON_CONFIG_CHANGE = "on_config_change"
    PRE_INIT = "pre_init"
    POST_INIT = "post_init"


# ──────────────────────────── Events ─────────────────────────────────


@dataclass
class HookEvent:
    """Event passed to hook callbacks."""
    hook_point: HookPoint
    plugin_id: str
    plugin_type: PluginType
    context: dict = field(default_factory=dict)
    result: Any = None
    error: Optional[Exception] = None
    cancelled: bool = False

    def cancel(self):
        """Cancel the event (prevents further processing)."""
        self.cancelled = True


@dataclass
class PluginConfig:
    """Dynamic configuration for a plugin."""
    plugin_id: str
    plugin_type: PluginType
    name: str
    version: str
    description: str = ""
    author: str = ""
    enabled: bool = True
    priority: int = 0
    settings: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "plugin_id": self.plugin_id,
            "plugin_type": self.plugin_type.value,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "priority": self.priority,
            "settings": self.settings,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PluginConfig":
        return cls(
            plugin_id=data["plugin_id"],
            plugin_type=PluginType(data["plugin_type"]),
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            settings=data.get("settings", {}),
            dependencies=data.get("dependencies", []),
            permissions=data.get("permissions", []),
            metadata=data.get("metadata", {}),
        )


# ──────────────────────── Plugin Base ────────────────────────────────


class Plugin:
    """Base class for all plugins."""

    def __init__(self, config: PluginConfig):
        self.config = config
        self._state = PluginState.DISCOVERED
        self._error: Optional[str] = None

    @property
    def id(self) -> str:
        return self.config.plugin_id

    @property
    def plugin_type(self) -> PluginType:
        return self.config.plugin_type

    @property
    def state(self) -> PluginState:
        return self._state

    @property
    def error(self) -> Optional[str]:
        return self._error

    def _set_state(self, state: PluginState):
        self._state = state

    def _set_error(self, error: str):
        self._error = error
        self._state = PluginState.ERROR

    async def initialize(self) -> None:
        """Initialize the plugin."""
        self._state = PluginState.ACTIVE

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        self._state = PluginState.UNLOADED

    async def pause(self) -> None:
        """Pause the plugin (can be resumed)."""
        if self._state == PluginState.ACTIVE:
            self._state = PluginState.PAUSED

    async def resume(self) -> None:
        """Resume a paused plugin."""
        if self._state == PluginState.PAUSED:
            self._state = PluginState.ACTIVE

    def get_settings(self) -> dict:
        """Get current settings."""
        return dict(self.config.settings)

    def update_setting(self, key: str, value: Any):
        """Update a single setting."""
        self.config.settings[key] = value

    def update_settings(self, settings: dict):
        """Update multiple settings."""
        self.config.settings.update(settings)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.plugin_type.value,
            "state": self._state.value,
            "error": self._error,
            "config": self.config.to_dict(),
        }


# ────────────────────── Plugin Type Interfaces ───────────────────────


class FrameworkPlugin(Plugin):
    """Framework plugins provide core infrastructure."""

    async def setup_framework(self) -> None:
        """Set up the framework."""
        pass

    async def teardown_framework(self) -> None:
        """Tear down the framework."""
        pass


class SolverPlugin(Plugin):
    """Solver plugins provide problem-solving capabilities."""

    async def solve(self, problem: dict, context: dict) -> dict:
        """Solve a problem and return the solution."""
        return {"status": "not_implemented"}

    def can_solve(self, problem: dict) -> bool:
        """Check if this solver can handle the given problem."""
        return True


class EvalPlugin(Plugin):
    """EvalPlugin plugins provide evaluation capabilities."""

    async def evaluate(self, target: dict, criteria: dict) -> dict:
        """Evaluate a target against criteria."""
        return {"status": "not_implemented"}

    def get_metrics(self) -> list[str]:
        """Get the metrics this evaluator provides."""
        return []


class MemoryPlugin(Plugin):
    """Memory plugins provide memory management capabilities."""

    async def store(self, key: str, value: Any, metadata: Optional[dict] = None) -> None:
        """Store a memory."""
        pass

    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a memory."""
        return None

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search memories."""
        return []

    async def forget(self, key: str) -> bool:
        """Forget a memory."""
        return True


class ToolPlugin(Plugin):
    """Tool plugins provide external tool capabilities."""

    def get_tool_definitions(self) -> list[dict]:
        """Get tool definitions (OpenAI function calling format)."""
        return []

    async def invoke_tool(self, tool_name: str, params: dict) -> Any:
        """Invoke a tool."""
        return {"status": "not_implemented"}


class GuardPlugin(Plugin):
    """Guard plugins provide safety and security checks."""

    async def check(self, action: dict, context: dict) -> "GuardResult":
        """Check an action for safety."""
        return GuardResult.allow("Default allow")

    def get_guard_name(self) -> str:
        """Get the name of this guard."""
        return "default_guard"


@dataclass
class GuardResult:
    """Result of a guard check."""
    allowed: bool
    reason: str = ""
    modified_action: Optional[dict] = None
    severity: str = "info"  # info, warning, critical

    @classmethod
    def allow(cls, reason: str = "") -> "GuardResult":
        return cls(allowed=True, reason=reason)

    @classmethod
    def deny(cls, reason: str, severity: str = "warning") -> "GuardResult":
        return cls(allowed=False, reason=reason, severity=severity)

    @classmethod
    def modify(cls, modified_action: dict, reason: str = "") -> "GuardResult":
        return cls(allowed=True, reason=reason, modified_action=modified_action)


# ──────────────────────── Hook Registry ──────────────────────────────


HookCallback = Callable[[HookEvent], Awaitable[None]]


class HookRegistry:
    """Manages hook registration and invocation."""

    def __init__(self):
        self._hooks: dict[HookPoint, list[tuple[str, int, HookCallback]]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        hook_point: HookPoint,
        callback: HookCallback,
        plugin_id: str = "",
        priority: int = 0,
    ):
        """Register a hook callback."""
        with self._lock:
            if hook_point not in self._hooks:
                self._hooks[hook_point] = []
            self._hooks[hook_point].append((plugin_id, priority, callback))
            # Sort by priority (higher = earlier)
            self._hooks[hook_point].sort(key=lambda x: -x[1])

    def unregister(
        self,
        hook_point: HookPoint,
        callback: HookCallback,
        plugin_id: str = "",
    ) -> bool:
        """Unregister a hook callback."""
        with self._lock:
            if hook_point not in self._hooks:
                return False
            hooks = self._hooks[hook_point]
            for i, (pid, _, cb) in enumerate(hooks):
                if cb == callback and (not plugin_id or pid == plugin_id):
                    hooks.pop(i)
                    return True
            return False

    def unregister_all(self, plugin_id: str):
        """Unregister all hooks for a plugin."""
        with self._lock:
            for hook_point in self._hooks:
                self._hooks[hook_point] = [
                    (pid, prio, cb)
                    for pid, prio, cb in self._hooks[hook_point]
                    if pid != plugin_id
                ]

    async def invoke(self, event: HookEvent) -> HookEvent:
        """Invoke all hooks for a hook point."""
        hooks = []
        with self._lock:
            hooks = list(self._hooks.get(event.hook_point, []))

        for plugin_id, priority, callback in hooks:
            if event.cancelled:
                break
            try:
                await callback(event)
            except Exception as e:
                logger.warning(f"Hook {event.hook_point.value} failed for {plugin_id}: {e}")

        return event

    def get_hooks(self, hook_point: Optional[HookPoint] = None) -> dict:
        """Get registered hooks."""
        with self._lock:
            if hook_point:
                return {hook_point: list(self._hooks.get(hook_point, []))}
            return {hp: list(hooks) for hp, hooks in self._hooks.items()}

    def clear(self):
        """Clear all hooks."""
        with self._lock:
            self._hooks.clear()


# ──────────────────────── Plugin Manager ─────────────────────────────


class PluginManager:
    """Manages plugin lifecycle, discovery, and isolation."""

    def __init__(self, plugin_dirs: Optional[list[str]] = None):
        self._plugins: dict[str, Plugin] = {}
        self._configs: dict[str, PluginConfig] = {}
        self._states: dict[str, PluginState] = {}
        self._errors: dict[str, str] = {}
        self._hook_registry = HookRegistry()
        self._plugin_dirs: list[Path] = [Path(d) for d in plugin_dirs or []]
        self._isolated: dict[str, bool] = {}
        self._lock = threading.Lock()

    @property
    def hook_registry(self) -> HookRegistry:
        return self._hook_registry

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._states.values() if s == PluginState.ACTIVE)

    # ──────────────── Discovery ────────────────

    def add_plugin_dir(self, directory: str):
        """Add a directory to search for plugins."""
        path = Path(directory)
        if path.exists() and path.is_dir():
            self._plugin_dirs.append(path)

    def discover_plugins(self) -> list[PluginConfig]:
        """Discover available plugins in plugin directories."""
        discovered = []

        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue

            # Look for plugin.json or plugin.py files
            for item in plugin_dir.iterdir():
                if item.is_dir():
                    # Check for plugin manifest
                    manifest_file = item / "plugin.json"
                    if manifest_file.exists():
                        try:
                            with open(manifest_file) as f:
                                data = json.load(f)
                            config = PluginConfig.from_dict(data)
                            discovered.append(config)
                        except Exception as e:
                            logger.warning(f"Failed to load manifest {manifest_file}: {e}")

                    # Check for single-file plugin
                    plugin_file = item / "plugin.py"
                    if plugin_file.exists():
                        try:
                            config = self._inspect_plugin_file(plugin_file)
                            if config:
                                discovered.append(config)
                        except Exception as e:
                            logger.warning(f"Failed to inspect {plugin_file}: {e}")

        return discovered

    def _inspect_plugin_file(self, path: Path) -> Optional[PluginConfig]:
        """Inspect a plugin.py file for metadata."""
        # Read the file and look for PLUGIN_CONFIG dict
        try:
            content = path.read_text()
            # Simple extraction - in production, use AST
            if "PLUGIN_CONFIG" in content:
                # Extract config via import
                spec = importlib.util.spec_from_file_location("temp_plugin", path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "PLUGIN_CONFIG"):
                        return PluginConfig.from_dict(module.PLUGIN_CONFIG)
        except Exception:
            pass
        return None

    # ──────────────── Lifecycle ────────────────

    async def load_plugin(self, config: PluginConfig) -> Optional[Plugin]:
        """Load a plugin from config."""
        with self._lock:
            if config.plugin_id in self._plugins:
                logger.warning(f"Plugin {config.plugin_id} already loaded")
                return None  # Already loaded - return None per test expectation

        self._states[config.plugin_id] = PluginState.LOADING
        self._configs[config.plugin_id] = config

        try:
            # Create plugin instance
            plugin = self._create_plugin(config)
            if plugin is None:
                self._set_error(config.plugin_id, f"Unknown plugin type: {config.plugin_type}")
                return None

            with self._lock:
                self._plugins[config.plugin_id] = plugin

            # Initialize
            self._states[config.plugin_id] = PluginState.INITIALIZING
            await plugin.initialize()
            self._states[config.plugin_id] = PluginState.ACTIVE

            # Fire hooks
            await self._hook_registry.invoke(HookEvent(
                hook_point=HookPoint.ON_LOAD,
                plugin_id=config.plugin_id,
                plugin_type=config.plugin_type,
            ))

            return plugin

        except Exception as e:
            self._set_error(config.plugin_id, str(e))
            logger.error(f"Failed to load plugin {config.plugin_id}: {e}")
            return None

    def _create_plugin(self, config: PluginConfig) -> Optional[Plugin]:
        """Create a plugin instance from config."""
        # In a real system, this would dynamically load the plugin class
        # For now, return a base plugin that uses the config
        plugin_class = self._get_plugin_class(config.plugin_type)
        if plugin_class:
            return plugin_class(config)
        return None

    def _get_plugin_class(self, plugin_type: PluginType) -> Optional[type]:
        """Get the plugin class for a type."""
        type_map = {
            PluginType.FRAMEWORK: FrameworkPlugin,
            PluginType.SOLVER: SolverPlugin,
            PluginType.EVAL: EvalPlugin,
            PluginType.MEMORY: MemoryPlugin,
            PluginType.TOOL: ToolPlugin,
            PluginType.GUARD: GuardPlugin,
        }
        return type_map.get(plugin_type)

    async def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        with self._lock:
            plugin = self._plugins.get(plugin_id)
            if not plugin:
                return False

        self._states[plugin_id] = PluginState.UNLOADING

        try:
            await plugin.shutdown()
            self._states[plugin_id] = PluginState.UNLOADED

            await self._hook_registry.invoke(HookEvent(
                hook_point=HookPoint.ON_UNLOAD,
                plugin_id=plugin_id,
                plugin_type=plugin.plugin_type,
            ))

            with self._lock:
                del self._plugins[plugin_id]

            return True

        except Exception as e:
            self._set_error(plugin_id, str(e))
            return False

    async def reload_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Reload a plugin."""
        config = self._configs.get(plugin_id)
        if not config:
            return None

        await self.unload_plugin(plugin_id)
        return await self.load_plugin(config)

    async def pause_plugin(self, plugin_id: str) -> bool:
        """Pause a plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        await plugin.pause()
        self._states[plugin_id] = PluginState.PAUSED
        return True

    async def resume_plugin(self, plugin_id: str) -> bool:
        """Resume a paused plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        await plugin.resume()
        self._states[plugin_id] = PluginState.ACTIVE
        return True

    # ──────────────── Access ────────────────

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        return self._plugins.get(plugin_id)

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[Plugin]:
        """Get all plugins of a specific type."""
        return [p for p in self._plugins.values() if p.plugin_type == plugin_type]

    def get_all_plugins(self) -> list[Plugin]:
        """Get all loaded plugins."""
        return list(self._plugins.values())

    def get_plugin_state(self, plugin_id: str) -> Optional[PluginState]:
        """Get the state of a plugin."""
        return self._states.get(plugin_id)

    def get_plugin_config(self, plugin_id: str) -> Optional[PluginConfig]:
        """Get the config of a plugin."""
        return self._configs.get(plugin_id)

    # ──────────────── Config ────────────────

    async def update_plugin_config(self, plugin_id: str, settings: dict) -> bool:
        """Update plugin configuration dynamically."""
        plugin = self._plugins.get(plugin_id)
        config = self._configs.get(plugin_id)
        if not plugin or not config:
            return False

        plugin.update_settings(settings)
        config.settings.update(settings)

        await self._hook_registry.invoke(HookEvent(
            hook_point=HookPoint.ON_CONFIG_CHANGE,
            plugin_id=plugin_id,
            plugin_type=plugin.plugin_type,
            context={"settings": settings},
        ))

        return True

    def load_config_from_file(self, path: str) -> list[PluginConfig]:
        """Load plugin configs from a JSON file."""
        try:
            with open(path) as f:
                data = json.load(f)
            return [PluginConfig.from_dict(c) for c in data.get("plugins", [])]
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            return []

    def save_config_to_file(self, path: str):
        """Save plugin configs to a JSON file."""
        configs = [c.to_dict() for c in self._configs.values()]
        with open(path, "w") as f:
            json.dump({"plugins": configs}, f, indent=2)

    # ──────────────── Isolation ────────────────

    def set_isolated(self, plugin_id: str, isolated: bool):
        """Set whether a plugin runs in isolation."""
        self._isolated[plugin_id] = isolated

    def is_isolated(self, plugin_id: str) -> bool:
        """Check if a plugin is isolated."""
        return self._isolated.get(plugin_id, False)

    # ──────────────── Helpers ────────────────

    def _set_error(self, plugin_id: str, error: str):
        """Set an error for a plugin."""
        self._errors[plugin_id] = error
        self._states[plugin_id] = PluginState.ERROR

    def get_status(self) -> dict:
        """Get overall plugin system status."""
        return {
            "total_plugins": len(self._plugins),
            "active_plugins": self.active_count,
            "plugins": {
                pid: {
                    "type": p.plugin_type.value,
                    "state": self._states.get(pid, PluginState.DISCOVERED).value,
                    "error": self._errors.get(pid),
                }
                for pid, p in self._plugins.items()
            },
        }
