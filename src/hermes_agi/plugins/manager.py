"""
Plugin System — Dynamic, Async, Production-Grade.

All capabilities are plugins. Plugins can depend on other plugins.
The system auto-loads, hot-reloads, and self-heals.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
import time
import traceback
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ──────────────────────────── Enums ────────────────────────────


class PluginState(str, Enum):
    REGISTERED = "registered"
    LOADING = "loading"
    LOADED = "loaded"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


class PluginPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


# ──────────────────────────── Exceptions ────────────────────────────


class PluginError(Exception):
    """Base plugin exception."""
    def __init__(self, message: str, plugin_name: str = None, cause: Exception = None):
        self.plugin_name = plugin_name
        self.cause = cause
        super().__init__(f"[{plugin_name}] {message}" if plugin_name else message)


class PluginLoadError(PluginError):
    """Plugin failed to load."""
    pass


class PluginStartError(PluginError):
    """Plugin failed to start."""
    pass


class PluginDependencyError(PluginError):
    """Plugin dependency not satisfied."""
    pass


class PluginTimeoutError(PluginError):
    """Plugin operation timed out."""
    pass


class PluginRecoveryError(PluginError):
    """Plugin recovery failed."""
    pass


# ──────────────────────────── Data Classes ────────────────────────────


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    priority: PluginPriority = PluginPriority.MEDIUM
    provides: list[str] = field(default_factory=list)
    consumes: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    health_check_interval: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 60.0
    tags: list[str] = field(default_factory=list)
    category: str = "general"


@dataclass
class PluginHealth:
    """Plugin health status."""
    state: PluginState
    last_check: float = 0
    last_error: str = ""
    error_count: int = 0
    total_errors: int = 0
    recovery_attempts: int = 0
    uptime: float = 0
    avg_response_time: float = 0
    last_response_time: float = 0


@dataclass
class PluginEvent:
    """Plugin lifecycle event."""
    event_id: str
    plugin_name: str
    event_type: str
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)


# ──────────────────────────── Plugin Base ────────────────────────────


class PluginBase:
    """
    Base class for all plugins.
    
    Plugins are async-first, with automatic health checking,
    self-recovery, and graceful degradation.
    """
    
    PLUGIN_METADATA: PluginMetadata = None
    
    def __init__(self, config: dict[str, Any] = None):
        self.metadata = self.PLUGIN_METADATA or PluginMetadata(name=self.__class__.__name__)
        self.config = config or {}
        self.state = PluginState.REGISTERED
        self.health = PluginHealth(state=PluginState.REGISTERED)
        self._start_time = 0
        self._lock = asyncio.Lock()
        self._dependencies: dict[str, PluginBase] = {}
        self._event_handlers: list[Callable] = []
        self._health_task: asyncio.Task = None
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"plugin-{self.metadata.name}")
    
    @property
    def name(self) -> str:
        return self.metadata.name
    
    @property
    def is_running(self) -> bool:
        return self.state == PluginState.RUNNING
    
    @property
    def is_healthy(self) -> bool:
        return self.health.state in (PluginState.RUNNING, PluginState.LOADED)
    
    async def load(self) -> bool:
        """Load the plugin."""
        try:
            self.state = PluginState.LOADING
            self._emit_event("loading")
            await self._on_load()
            self.state = PluginState.LOADED
            self.health.state = PluginState.LOADED
            self._emit_event("loaded")
            return True
        except Exception as e:
            self.state = PluginState.ERROR
            self.health.state = PluginState.ERROR
            self.health.last_error = str(e)
            self.health.error_count += 1
            self._emit_event("error", {"error": str(e)})
            logger.error(f"Plugin {self.name} load failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the plugin."""
        try:
            self.state = PluginState.STARTING
            self._emit_event("starting")
            await self._on_start()
            self.state = PluginState.RUNNING
            self.health.state = PluginState.RUNNING
            self._start_time = time.time()
            self._health_task = asyncio.create_task(self._health_check_loop())
            self._emit_event("started")
            return True
        except Exception as e:
            self.state = PluginState.ERROR
            self.health.state = PluginState.ERROR
            self.health.last_error = str(e)
            self.health.error_count += 1
            self._emit_event("error", {"error": str(e)})
            logger.error(f"Plugin {self.name} start failed: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the plugin."""
        try:
            self.state = PluginState.STOPPING
            self._emit_event("stopping")
            if self._health_task:
                self._health_task.cancel()
            await self._on_stop()
            self.state = PluginState.STOPPED
            self.health.state = PluginState.STOPPED
            self._emit_event("stopped")
            return True
        except Exception as e:
            self.state = PluginState.ERROR
            self.health.last_error = str(e)
            logger.error(f"Plugin {self.name} stop failed: {e}")
            return False
    
    async def unload(self) -> bool:
        """Unload the plugin."""
        try:
            self.state = PluginState.UNLOADING
            if self.is_running:
                await self.stop()
            await self._on_unload()
            self.state = PluginState.UNLOADED
            self._emit_event("unloaded")
            return True
        except Exception as e:
            self.state = PluginState.ERROR
            logger.error(f"Plugin {self.name} unload failed: {e}")
            return False
    
    async def execute(self, action: str, **kwargs) -> Any:
        """Execute a plugin action."""
        if not self.is_running:
            raise PluginError(f"Plugin {self.name} is not running", self.name)
        
        start = time.time()
        try:
            result = await asyncio.wait_for(
                self._on_execute(action, **kwargs),
                timeout=self.metadata.timeout
            )
            elapsed = time.time() - start
            self.health.last_response_time = elapsed
            self.health.avg_response_time = (
                (self.health.avg_response_time + elapsed) / 2
                if self.health.avg_response_time
                else elapsed
            )
            return result
        except asyncio.TimeoutError:
            raise PluginTimeoutError(f"Action {action} timed out", self.name)
        except Exception as e:
            self.health.error_count += 1
            self.health.total_errors += 1
            raise PluginError(f"Action {action} failed: {e}", self.name, e)
    
    async def health_check(self) -> dict[str, Any]:
        """Check plugin health."""
        try:
            result = await self._on_health_check()
            return {"healthy": True, "state": self.state.value, **result}
        except Exception as e:
            return {"healthy": False, "state": self.state.value, "error": str(e)}
    
    async def recover(self) -> bool:
        """Attempt to recover from error."""
        self.state = PluginState.RECOVERING
        self.health.recovery_attempts += 1
        self._emit_event("recovering")
        
        for attempt in range(self.metadata.max_retries):
            try:
                logger.info(f"Recovery attempt {attempt + 1} for {self.name}")
                if self.is_running:
                    await self.stop()
                await self._on_recover()
                if await self.start():
                    self.health.error_count = 0
                    self._emit_event("recovered")
                    return True
            except Exception as e:
                logger.warning(f"Recovery attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.metadata.retry_delay * (2 ** attempt))
        
        self.state = PluginState.ERROR
        self._emit_event("recovery_failed")
        return False
    
    def get_capabilities(self) -> list[str]:
        """Get plugin capabilities."""
        return self.metadata.capabilities
    
    def provides(self, capability: str) -> bool:
        """Check if plugin provides a capability."""
        return capability in self.metadata.provides or capability in self.metadata.capabilities
    
    def add_event_handler(self, handler: Callable):
        """Add an event handler."""
        self._event_handlers.append(handler)
    
    def _emit_event(self, event_type: str, data: dict = None):
        """Emit a plugin event."""
        event = PluginEvent(
            event_id=str(uuid.uuid4())[:8],
            plugin_name=self.name,
            event_type=event_type,
            timestamp=time.time(),
            data=data or {},
        )
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.warning(f"Event handler error: {e}")
    
    async def _health_check_loop(self):
        """Periodic health check loop."""
        while self.is_running:
            try:
                await asyncio.sleep(self.metadata.health_check_interval)
                result = await self.health_check()
                self.health.last_check = time.time()
                if not result.get("healthy", False):
                    logger.warning(f"Health check failed for {self.name}: {result}")
                    if self.health.error_count < self.metadata.max_retries:
                        await self.recover()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error for {self.name}: {e}")
    
    # ── Override these in subclasses ──
    
    async def _on_load(self):
        """Override: load plugin."""
        pass
    
    async def _on_start(self):
        """Override: start plugin."""
        pass
    
    async def _on_stop(self):
        """Override: stop plugin."""
        pass
    
    async def _on_unload(self):
        """Override: unload plugin."""
        pass
    
    async def _on_execute(self, action: str, **kwargs) -> Any:
        """Override: execute action."""
        raise NotImplementedError
    
    async def _on_health_check(self) -> dict[str, Any]:
        """Override: health check."""
        return {}
    
    async def _on_recover(self):
        """Override: recover from error."""
        pass


# ──────────────────────────── Plugin Manager ────────────────────────────


class PluginManager:
    """
    Manages all plugins: load, start, stop, hot-reload, self-heal.
    
    Features:
    - Dependency resolution
    - Parallel loading and starting
    - Hot-reload on file change
    - Self-healing on failure
    - Graceful degradation
    - Event bus
    """
    
    def __init__(self, plugin_dirs: list[str] = None, max_workers: int = 4):
        self.plugin_dirs = plugin_dirs or []
        self.max_workers = max_workers
        self._plugins: dict[str, PluginBase] = {}
        self._capabilities: dict[str, list[str]] = defaultdict(list)
        self._event_handlers: list[Callable] = []
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="plugin-mgr")
        self._hot_reload_task: asyncio.Task = None
        self._file_mtimes: dict[str, float] = {}
    
    @property
    def plugins(self) -> dict[str, PluginBase]:
        return dict(self._plugins)
    
    @property
    def running_plugins(self) -> dict[str, PluginBase]:
        return {n: p for n, p in self._plugins.items() if p.is_running}
    
    def register(self, plugin: PluginBase) -> bool:
        """Register a plugin."""
        if plugin.name in self._plugins:
            logger.warning(f"Plugin {plugin.name} already registered")
            return False
        
        plugin.add_event_handler(self._on_plugin_event)
        self._plugins[plugin.name] = plugin
        
        # Register capabilities
        for cap in plugin.get_capabilities():
            self._capabilities[cap].append(plugin.name)
        
        logger.info(f"Registered plugin: {plugin.name}")
        return True
    
    def unregister(self, plugin_name: str) -> bool:
        """Unregister a plugin."""
        if plugin_name not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_name]
        for cap in plugin.get_capabilities():
            if plugin_name in self._capabilities[cap]:
                self._capabilities[cap].remove(plugin_name)
        
        del self._plugins[plugin_name]
        return True
    
    async def load_all(self) -> dict[str, bool]:
        """Load all registered plugins in dependency order."""
        results = {}
        ordered = self._resolve_dependencies()
        
        # Load in parallel batches
        for batch in self._batch_by_dependencies(ordered):
            batch_results = await asyncio.gather(
                *[self._load_plugin_safe(p) for p in batch],
                return_exceptions=True,
            )
            for plugin, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[plugin.name] = False
                    logger.error(f"Failed to load {plugin.name}: {result}")
                else:
                    results[plugin.name] = result
        
        return results
    
    async def start_all(self) -> dict[str, bool]:
        """Start all loaded plugins in dependency order."""
        results = {}
        ordered = self._resolve_dependencies()
        
        for batch in self._batch_by_dependencies(ordered):
            batch_results = await asyncio.gather(
                *[self._start_plugin_safe(p) for p in batch],
                return_exceptions=True,
            )
            for plugin, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[plugin.name] = False
                else:
                    results[plugin.name] = result
        
        return results
    
    async def stop_all(self) -> dict[str, bool]:
        """Stop all running plugins in reverse dependency order."""
        results = {}
        ordered = self._resolve_dependencies()
        ordered.reverse()
        
        for batch in self._batch_by_dependencies(ordered):
            batch_results = await asyncio.gather(
                *[self._stop_plugin_safe(p) for p in batch],
                return_exceptions=True,
            )
            for plugin, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[plugin.name] = False
                else:
                    results[plugin.name] = result
        
        return results
    
    async def load_from_directory(self, directory: str) -> dict[str, bool]:
        """Load all plugins from a directory."""
        results = {}
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.warning(f"Plugin directory not found: {directory}")
            return results
        
        for plugin_file in dir_path.glob("*/plugin.py"):
            try:
                plugin = self._load_plugin_from_file(plugin_file)
                if plugin:
                    self.register(plugin)
                    results[plugin.name] = True
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_file}: {e}")
                results[str(plugin_file)] = False
        
        return results
    
    async def execute(self, capability: str, action: str = "run", **kwargs) -> Any:
        """Execute an action on the best plugin for a capability."""
        plugin = self._find_best_plugin(capability)
        if not plugin:
            raise PluginError(f"No plugin provides capability: {capability}")
        
        return await plugin.execute(action, **kwargs)
    
    async def execute_parallel(self, capability: str, action: str = "run", **kwargs) -> list[Any]:
        """Execute an action on all plugins that provide a capability."""
        plugins = [p for p in self._plugins.values() if p.provides(capability) and p.is_running]
        
        if not plugins:
            raise PluginError(f"No running plugins provide capability: {capability}")
        
        results = await asyncio.gather(
            *[p.execute(action, **kwargs) for p in plugins],
            return_exceptions=True,
        )
        
        return [
            {"plugin": p.name, "result": r if not isinstance(r, Exception) else None, "error": str(r) if isinstance(r, Exception) else None}
            for p, r in zip(plugins, results)
        ]
    
    def find_by_capability(self, capability: str) -> list[PluginBase]:
        """Find plugins that provide a capability."""
        return [p for p in self._plugins.values() if p.provides(capability)]
    
    def find_by_category(self, category: str) -> list[PluginBase]:
        """Find plugins by category."""
        return [p for p in self._plugins.values() if p.metadata.category == category]
    
    def find_by_tag(self, tag: str) -> list[PluginBase]:
        """Find plugins by tag."""
        return [p for p in self._plugins.values() if tag in p.metadata.tags]
    
    def get_plugin(self, name: str) -> PluginBase | None:
        """Get a plugin by name."""
        return self._plugins.get(name)
    
    def get_capabilities(self) -> set[str]:
        """Get all available capabilities."""
        return set(self._capabilities.keys())
    
    async def health_check_all(self) -> dict[str, dict[str, Any]]:
        """Check health of all running plugins."""
        results = {}
        for name, plugin in self.running_plugins.items():
            results[name] = await plugin.health_check()
        return results
    
    async def recover_all(self) -> dict[str, bool]:
        """Attempt to recover all failed plugins."""
        results = {}
        for name, plugin in self._plugins.items():
            if plugin.state == PluginState.ERROR:
                results[name] = await plugin.recover()
        return results
    
    def add_event_handler(self, handler: Callable):
        """Add an event handler."""
        self._event_handlers.append(handler)
    
    async def _on_plugin_event(self, event: PluginEvent):
        """Handle plugin events."""
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.warning(f"Event handler error: {e}")
    
    def _find_best_plugin(self, capability: str) -> PluginBase | None:
        """Find the best running plugin for a capability."""
        candidates = [p for p in self._plugins.values() if p.provides(capability) and p.is_healthy]
        
        if not candidates:
            return None
        
        # Sort by priority, then by health (fewer errors first)
        candidates.sort(key=lambda p: (p.metadata.priority.value, p.health.error_count))
        return candidates[0]
    
    def _resolve_dependencies(self) -> list[PluginBase]:
        """Resolve plugin dependencies and return ordered list."""
        visited = set()
        order = []
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            plugin = self._plugins.get(name)
            if plugin:
                for dep in plugin.metadata.dependencies:
                    visit(dep)
                order.append(plugin)
        
        # Sort by priority first
        sorted_plugins = sorted(self._plugins.values(), key=lambda p: p.metadata.priority.value)
        for plugin in sorted_plugins:
            visit(plugin.name)
        
        return order
    
    def _batch_by_dependencies(self, ordered: list[PluginBase]) -> list[list[PluginBase]]:
        """Group plugins into batches that can be loaded in parallel."""
        batches = []
        loaded = set()
        
        for plugin in ordered:
            # Check if all dependencies are in previous batches
            deps_loaded = all(d in loaded for d in plugin.metadata.dependencies)
            
            if deps_loaded:
                # Add to current batch
                if not batches or not self._can_add_to_batch(batches[-1], plugin, loaded):
                    batches.append([])
                batches[-1].append(plugin)
                loaded.add(plugin.name)
            else:
                # Start a new batch
                batches.append([plugin])
                loaded.add(plugin.name)
        
        return batches
    
    def _can_add_to_batch(self, batch: list[PluginBase], plugin: PluginBase, loaded: set) -> bool:
        """Check if a plugin can be added to the current batch."""
        return all(d in loaded for d in plugin.metadata.dependencies)
    
    async def _load_plugin_safe(self, plugin: PluginBase) -> bool:
        """Safely load a plugin with error handling."""
        try:
            return await plugin.load()
        except Exception as e:
            logger.error(f"Error loading {plugin.name}: {e}")
            return False
    
    async def _start_plugin_safe(self, plugin: PluginBase) -> bool:
        """Safely start a plugin with error handling."""
        try:
            return await plugin.start()
        except Exception as e:
            logger.error(f"Error starting {plugin.name}: {e}")
            return False
    
    async def _stop_plugin_safe(self, plugin: PluginBase) -> bool:
        """Safely stop a plugin with error handling."""
        try:
            return await plugin.stop()
        except Exception as e:
            logger.error(f"Error stopping {plugin.name}: {e}")
            return False
    
    def _load_plugin_from_file(self, file_path: Path) -> PluginBase | None:
        """Load a plugin from a file."""
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find PluginBase subclass
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, PluginBase) and obj is not PluginBase:
                return obj()
        
        return None
    
    async def start_hot_reload(self, interval: float = 5.0):
        """Start hot-reload monitoring."""
        self._hot_reload_task = asyncio.create_task(self._hot_reload_loop(interval))
    
    async def stop_hot_reload(self):
        """Stop hot-reload monitoring."""
        if self._hot_reload_task:
            self._hot_reload_task.cancel()
    
    async def _hot_reload_loop(self, interval: float):
        """Monitor plugin files for changes."""
        while True:
            try:
                await asyncio.sleep(interval)
                for plugin_dir in self.plugin_dirs:
                    dir_path = Path(plugin_dir)
                    if dir_path.exists():
                        for plugin_file in dir_path.glob("*/plugin.py"):
                            mtime = plugin_file.stat().st_mtime
                            key = str(plugin_file)
                            if key in self._file_mtimes and self._file_mtimes[key] < mtime:
                                logger.info(f"Hot-reloading {plugin_file}")
                                await self._hot_reload_plugin(plugin_file)
                            self._file_mtimes[key] = mtime
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Hot-reload error: {e}")
    
    async def _hot_reload_plugin(self, file_path: Path):
        """Hot-reload a single plugin."""
        # Find the plugin
        for name, plugin in self._plugins.items():
            if name in str(file_path):
                await plugin.unload()
                new_plugin = self._load_plugin_from_file(file_path)
                if new_plugin:
                    self.register(new_plugin)
                    await new_plugin.load()
                    await new_plugin.start()
                break
    
    def status(self) -> dict[str, Any]:
        """Get full status."""
        return {
            "total_plugins": len(self._plugins),
            "running": len(self.running_plugins),
            "by_state": {
                state.value: sum(1 for p in self._plugins.values() if p.state == state)
                for state in PluginState
            },
            "by_category": {
                cat: len(self.find_by_category(cat))
                for cat in set(p.metadata.category for p in self._plugins.values())
            },
            "capabilities": len(self._capabilities),
            "plugins": {
                name: {
                    "state": p.state.value,
                    "healthy": p.is_healthy,
                    "capabilities": p.get_capabilities(),
                    "priority": p.metadata.priority.name,
                }
                for name, p in self._plugins.items()
            },
        }
