"""
Dynamic async configuration with hot-reload.

Provides a configuration manager that:
- Loads config from YAML/JSON files
- Supports environment variable overrides
- Hot-reloads on file change
- Notifies subscribers on config change
- Thread-safe async access
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Union


logger = logging.getLogger(__name__)

# Type alias for config change subscribers
ConfigCallback = Callable[[str, Any, Any], Awaitable[None]]


@dataclass
class ConfigChangeEvent:
    """Represents a configuration change."""
    key: str
    old_value: Any
    new_value: Any
    timestamp: float = field(default_factory=time.time)
    source: str = ""  # What triggered the change


class Config:
    """Dynamic async configuration manager.
    
    Supports loading from files, environment overrides, hot-reload,
    and subscriber notifications.
    
    Usage::
    
        config = Config()
        await config.load_file("config.yaml")
        value = config.get("key", default="fallback")
        config.set("key", "new_value")
    """

    def __init__(
        self,
        defaults: Optional[dict[str, Any]] = None,
        env_prefix: str = "HARNESS_",
        hot_reload: bool = False,
        reload_interval: float = 5.0,
    ) -> None:
        self._data: dict[str, Any] = defaults or {}
        self._env_prefix = env_prefix
        self._hot_reload = hot_reload
        self._reload_interval = reload_interval
        self._file_path: Optional[Path] = None
        self._file_mtime: float = 0.0
        self._subscribers: list[ConfigCallback] = []
        self._lock = asyncio.Lock()
        self._reload_task: Optional[asyncio.Task] = None
        self._change_log: list[ConfigChangeEvent] = []
        self._running = False

    @property
    def data(self) -> dict[str, Any]:
        """Get a copy of the current configuration data."""
        return copy.deepcopy(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Supports dot notation for nested keys (e.g., "database.host").
        """
        keys = key.split(".")
        value: Any = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    async def set(self, key: str, value: Any, source: str = "manual") -> None:
        """Set a configuration value.
        
        Supports dot notation for nested keys.
        Notifies subscribers of the change.
        """
        async with self._lock:
            keys = key.split(".")
            data = self._data
            
            for k in keys[:-1]:
                if k not in data or not isinstance(data[k], dict):
                    data[k] = {}
                data = data[k]
            
            old_value = data.get(keys[-1])
            data[keys[-1]] = value
        
        event = ConfigChangeEvent(
            key=key, old_value=old_value, new_value=value, source=source
        )
        self._change_log.append(event)
        
        await self._notify(key, old_value, value)

    async def delete(self, key: str) -> bool:
        """Delete a configuration key."""
        async with self._lock:
            keys = key.split(".")
            data = self._data
            for k in keys[:-1]:
                if isinstance(data, dict) and k in data:
                    data = data[k]
                else:
                    return False
            if keys[-1] in data:
                old_value = data.pop(keys[-1])
                event = ConfigChangeEvent(
                    key=key, old_value=old_value, new_value=None, source="delete"
                )
                self._change_log.append(event)
                await self._notify(key, old_value, None)
                return True
            return False

    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return self.get(key, ...) is not ...

    async def load_file(
        self, path: Union[str, Path], format: Optional[str] = None
    ) -> None:
        """Load configuration from a file.
        
        Supports YAML (.yaml, .yml) and JSON (.json) formats.
        
        Args:
            path: Path to the configuration file.
            format: Override auto-detection ('yaml' or 'json').
        """
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        content = path.read_text(encoding="utf-8")
        
        if format is None:
            format = "yaml" if path.suffix in (".yaml", ".yml") else "json"
        
        if format == "yaml":
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                raise RuntimeError(
                    "PyYAML is required for YAML config files. "
                    "Install it with: pip install pyyaml"
                )
        elif format == "json":
            data = json.loads(content)
        else:
            raise ValueError(f"Unsupported config format: {format}")
        
        if not isinstance(data, dict):
            raise ValueError("Config file must contain a mapping at the top level")
        
        async with self._lock:
            old_data = self._data
            self._data = data
            self._file_path = path
            self._file_mtime = path.stat().st_mtime
        
        # Notify for all top-level changes
        all_keys = set(old_data.keys()) | set(data.keys())
        for key in all_keys:
            old_val = old_data.get(key)
            new_val = data.get(key)
            if old_val != new_val:
                await self._notify(key, old_val, new_val)

    async def load_env(self, prefix: Optional[str] = None) -> int:
        """Load configuration from environment variables.
        
        Environment variables with the given prefix are loaded as config keys.
        Double underscore (__) denotes nesting.
        
        Example::
            
            HARNESS_DATABASE__HOST=localhost  ->  database.host = "localhost"
        
        Args:
            prefix: Override the instance env_prefix.
            
        Returns:
            Number of environment variables loaded.
        """
        prefix = prefix or self._env_prefix
        count = 0
        
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            
            config_key = key[len(prefix):].lower().replace("__", ".")
            # Try to parse as JSON for complex types
            try:
                parsed = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                parsed = value
            
            await self.set(config_key, parsed, source="env")
            count += 1
        
        return count

    async def merge(self, other: dict[str, Any], source: str = "merge") -> None:
        """Merge a dictionary into the current configuration."""
        async with self._lock:
            self._deep_merge(self._data, other)
        
        for key in other:
            await self._notify(key, None, other[key])

    def _deep_merge(self, base: dict[str, Any], overlay: dict[str, Any]) -> None:
        """Recursively merge overlay into base."""
        for key, value in overlay.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def subscribe(self, callback: ConfigCallback) -> Callable[[], None]:
        """Subscribe to configuration changes.
        
        Returns an unsubscribe function.
        """
        self._subscribers.append(callback)
        
        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        
        return unsubscribe

    async def _notify(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify all subscribers of a change."""
        for callback in self._subscribers:
            try:
                await callback(key, old_value, new_value)
            except Exception:
                logger.exception("Config subscriber raised an exception")

    async def start_hot_reload(self) -> None:
        """Start hot-reload background task."""
        if not self._file_path:
            raise RuntimeError("No config file loaded")
        if self._running:
            return
        
        self._running = True
        self._reload_task = asyncio.create_task(self._reload_loop())

    async def stop_hot_reload(self) -> None:
        """Stop hot-reload background task."""
        self._running = False
        if self._reload_task:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass
            self._reload_task = None

    async def _reload_loop(self) -> None:
        """Background loop that checks for file changes."""
        while self._running:
            try:
                await asyncio.sleep(self._reload_interval)
                if self._file_path and self._file_path.exists():
                    mtime = self._file_path.stat().st_mtime
                    if mtime > self._file_mtime:
                        logger.info("Config file changed, reloading: %s", self._file_path)
                        await self.load_file(self._file_path)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in config reload loop")

    def get_change_log(self, limit: int = 100) -> list[ConfigChangeEvent]:
        """Get the configuration change history."""
        return self._change_log[-limit:]

    def clear_change_log(self) -> None:
        """Clear the change history."""
        self._change_log.clear()

    def snapshot(self) -> dict[str, Any]:
        """Create a snapshot of the current configuration."""
        return copy.deepcopy(self._data)

    async def restore(self, snapshot: dict[str, Any]) -> None:
        """Restore configuration from a snapshot."""
        async with self._lock:
            self._data = copy.deepcopy(snapshot)

    def __repr__(self) -> str:
        return f"Config(keys={len(self._data)}, hot_reload={self._hot_reload})"
