"""Dynamic configuration with hot-reload (<5s)."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ConfigChangeEvent:
    """A configuration change event."""
    key: str
    old_value: Any
    new_value: Any
    timestamp: float
    source: str


class DynamicConfig:
    """Thread-safe dynamic configuration with hot-reload."""

    def __init__(self, config_path: str = "./config.json", reload_interval: float = 2.0):
        self._config_path = config_path
        self._reload_interval = reload_interval
        self._lock = threading.RLock()
        self._config: dict[str, Any] = {}
        self._last_modified: float = 0.0
        self._last_check: float = 0.0
        self._running = False
        self._reload_thread: threading.Thread | None = None
        self._listeners: list[Callable[[ConfigChangeEvent], None]] = []
        self._change_log: list[ConfigChangeEvent] = []

    def start(self) -> None:
        """Start the hot-reload background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._reload_thread = threading.Thread(target=self._reload_loop, daemon=True)
            self._reload_thread.start()

    def stop(self) -> None:
        """Stop the hot-reload background thread."""
        with self._lock:
            self._running = False
        if self._reload_thread:
            self._reload_thread.join(timeout=5.0)

    def _reload_loop(self) -> None:
        while self._running:
            self._check_and_reload()
            time.sleep(self._reload_interval)

    def _check_and_reload(self) -> None:
        try:
            if not os.path.exists(self._config_path):
                return
            mtime = os.path.getmtime(self._config_path)
            if mtime > self._last_modified:
                self._last_modified = mtime
                self._load_config()
        except OSError:
            pass

    def _load_config(self) -> None:
        try:
            with open(self._config_path) as f:
                new_config = json.load(f)
            with self._lock:
                old_config = dict(self._config)
                changes = self._detect_changes(old_config, new_config)
                self._config = new_config
            # Notify listeners
            for change in changes:
                self._change_log.append(change)
                for listener in self._listeners:
                    try:
                        listener(change)
                    except Exception:
                        pass
        except (json.JSONDecodeError, OSError):
            pass

    def _detect_changes(self, old: dict[str, Any], new: dict[str, Any]) -> list[ConfigChangeEvent]:
        changes = []
        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                changes.append(ConfigChangeEvent(
                    key=key,
                    old_value=old_val,
                    new_value=new_val,
                    timestamp=time.time(),
                    source="file",
                ))
        return changes

    def load(self, path: str | None = None) -> None:
        """Load config from file."""
        with self._lock:
            path = path or self._config_path
            if os.path.exists(path):
                with open(path) as f:
                    self._config = json.load(f)
                self._last_modified = os.path.getmtime(path)

    def save(self, path: str | None = None) -> None:
        """Save config to file."""
        with self._lock:
            path = path or self._config_path
            dir_name = os.path.dirname(path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(path, "w") as f:
                json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            old = self._config.get(key)
            self._config[key] = value
            if old != value:
                change = ConfigChangeEvent(
                    key=key,
                    old_value=old,
                    new_value=value,
                    timestamp=time.time(),
                    source="api",
                )
                self._change_log.append(change)
                for listener in self._listeners:
                    try:
                        listener(change)
                    except Exception:
                        pass

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def add_listener(self, listener: Callable[[ConfigChangeEvent], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> bool:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)
                return True
            return False

    def get_change_log(self) -> list[ConfigChangeEvent]:
        with self._lock:
            return list(self._change_log)

    def clear_log(self) -> None:
        with self._lock:
            self._change_log.clear()


__all__ = ["ConfigChangeEvent", "DynamicConfig"]
