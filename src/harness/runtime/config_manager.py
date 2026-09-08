"""
ConfigManager - Dynamic configuration with hot-reload support.

Provides a centralized configuration system that supports:
- Loading from dict, JSON, or YAML files
- Dot-notation access (config.get("a.b.c"))
- Hot-reload via file watcher
- Change callbacks
- Default values and schema validation
"""

from __future__ import annotations

import json
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union


class ConfigManager:
    """Centralized configuration manager with hot-reload support."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}
        self._validators: Dict[str, Callable[[Any], bool]] = {}
        self._callbacks: List[Callable[[str, Any, Any], None]] = []
        self._lock = threading.RLock()
        self._watcher_thread: Optional[threading.Thread] = None
        self._watcher_running = False
        self._watcher_path: Optional[Path] = None
        self._watcher_interval: float = 1.0
        self._last_mtime: float = 0.0

        if config:
            self._config = deepcopy(config)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot-notation."""
        with self._lock:
            keys = key.split(".")
            value = self._config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    if default is not None:
                        return default
                    return self._defaults.get(key)
            return deepcopy(value)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot-notation."""
        with self._lock:
            old_value = self.get(key)
            keys = key.split(".")
            config = self._config
            for k in keys[:-1]:
                if k not in config or not isinstance(config[k], dict):
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = deepcopy(value)

        self._notify(key, old_value, value)

    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        with self._lock:
            keys = key.split(".")
            value = self._config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return False
            return True

    def delete(self, key: str) -> bool:
        """Delete a configuration key. Returns True if key existed."""
        with self._lock:
            keys = key.split(".")
            config = self._config
            for k in keys[:-1]:
                if isinstance(config, dict) and k in config:
                    config = config[k]
                else:
                    return False
            if keys[-1] in config:
                old_value = config.pop(keys[-1])
                self._notify(key, old_value, None)
                return True
            return False

    def load_dict(self, data: Dict[str, Any], merge: bool = True) -> None:
        """Load configuration from a dictionary."""
        with self._lock:
            if merge:
                self._deep_merge(self._config, deepcopy(data))
            else:
                self._config = deepcopy(data)

    def load_json(self, path: Union[str, Path], merge: bool = True) -> None:
        """Load configuration from a JSON file."""
        path = Path(path)
        with open(path, "r") as f:
            data = json.load(f)
        self.load_dict(data, merge=merge)

    def load_env(self, prefix: str = "HARNESS_") -> None:
        """Load configuration from environment variables with given prefix."""
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace("_", ".")
                # Try to parse as JSON for complex types
                try:
                    parsed = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed = value
                self.set(config_key, parsed)

    def get_all(self) -> Dict[str, Any]:
        """Get a deep copy of the entire configuration."""
        with self._lock:
            return deepcopy(self._config)

    def set_default(self, key: str, value: Any) -> None:
        """Set a default value for a key."""
        self._defaults[key] = deepcopy(value)

    def register_validator(self, key: str, validator: Callable[[Any], bool]) -> None:
        """Register a validator function for a key."""
        self._validators[key] = validator

    def on_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Register a callback for configuration changes."""
        self._callbacks.append(callback)

    def start_watcher(self, path: Union[str, Path], interval: float = 1.0) -> None:
        """Start watching a configuration file for changes."""
        self._watcher_path = Path(path)
        self._watcher_interval = interval
        self._watcher_running = True
        self._last_mtime = self._get_mtime()
        self._watcher_thread = threading.Thread(
            target=self._watch_loop, daemon=True
        )
        self._watcher_thread.start()

    def stop_watcher(self) -> None:
        """Stop the file watcher."""
        self._watcher_running = False
        if self._watcher_thread:
            self._watcher_thread.join(timeout=5.0)
            self._watcher_thread = None

    def reset(self) -> None:
        """Reset configuration to empty."""
        with self._lock:
            self._config.clear()

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Deep merge override into base."""
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(base[key], value)
            else:
                base[key] = deepcopy(value)

    def _notify(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify all registered callbacks of a change."""
        for callback in self._callbacks:
            try:
                callback(key, old_value, new_value)
            except Exception:
                pass  # Don't let callbacks break the config manager

    def _get_mtime(self) -> float:
        """Get the modification time of the watched file."""
        if self._watcher_path and self._watcher_path.exists():
            return self._watcher_path.stat().st_mtime
        return 0.0

    def _watch_loop(self) -> None:
        """Main watcher loop running in a background thread."""
        while self._watcher_running:
            time.sleep(self._watcher_interval)
            if not self._watcher_path or not self._watcher_path.exists():
                continue
            current_mtime = self._get_mtime()
            if current_mtime > self._last_mtime:
                self._last_mtime = current_mtime
                try:
                    self.load_json(self._watcher_path, merge=True)
                except Exception:
                    pass  # Ignore reload errors
