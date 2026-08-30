"""Plugin base class and metadata."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class PluginStatus(Enum):
    """Status of a plugin."""
    REGISTERED = "registered"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"
    UNREGISTERED = "unregistered"


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    config_schema: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if not self.provides:
            self.provides = [self.id]


class Plugin:
    """Base class for all plugins."""

    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self.status = PluginStatus.REGISTERED
        self._lock = threading.RLock()
        self._config: dict[str, Any] = {}
        self._error: Optional[str] = None
        self._load_time: float = 0.0
        self._init_time: float = 0.0
        self._last_error_time: float = 0.0
        self._error_count = 0

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def is_active(self) -> bool:
        return self.status == PluginStatus.ACTIVE

    @property
    def has_error(self) -> bool:
        return self.status == PluginStatus.ERROR

    def get_status(self) -> PluginStatus:
        with self._lock:
            return self.status

    def set_status(self, status: PluginStatus) -> None:
        with self._lock:
            self.status = status

    def set_config(self, config: dict[str, Any]) -> None:
        with self._lock:
            self._config = dict(config)

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def record_error(self, error: str) -> None:
        with self._lock:
            self._error = error
            self._last_error_time = time.time()
            self._error_count += 1
            self.status = PluginStatus.ERROR

    def clear_error(self) -> None:
        with self._lock:
            self._error = None

    def get_error(self) -> Optional[str]:
        with self._lock:
            return self._error

    def get_error_count(self) -> int:
        with self._lock:
            return self._error_count

    def on_load(self) -> None:
        """Called when the plugin is loaded."""
        with self._lock:
            self.status = PluginStatus.LOADING
            start = time.time()
            try:
                self._do_load()
                self._load_time = time.time() - start
                self.status = PluginStatus.LOADED
            except Exception as e:
                self.record_error(str(e))
                raise

    def on_init(self) -> None:
        """Called when the plugin is initialized."""
        with self._lock:
            if self.status == PluginStatus.ERROR:
                return
            self.status = PluginStatus.INITIALIZING
            start = time.time()
            try:
                self._do_init()
                self._init_time = time.time() - start
                self.status = PluginStatus.ACTIVE
            except Exception as e:
                self.record_error(str(e))
                raise

    def on_pause(self) -> None:
        """Called when the plugin is paused."""
        with self._lock:
            if self.status == PluginStatus.ACTIVE:
                self.status = PluginStatus.PAUSED
                self._do_pause()

    def on_resume(self) -> None:
        """Called when the plugin is resumed."""
        with self._lock:
            if self.status == PluginStatus.PAUSED:
                self._do_resume()
                self.status = PluginStatus.ACTIVE

    def on_stop(self) -> None:
        """Called when the plugin is stopped."""
        with self._lock:
            self.status = PluginStatus.STOPPING
            try:
                self._do_stop()
            except Exception as e:
                self.record_error(str(e))
            finally:
                self.status = PluginStatus.STOPPED

    def _do_load(self) -> None:
        """Override to implement load logic."""
        pass

    def _do_init(self) -> None:
        """Override to implement init logic."""
        pass

    def _do_pause(self) -> None:
        """Override to implement pause logic."""
        pass

    def _do_resume(self) -> None:
        """Override to implement resume logic."""
        pass

    def _do_stop(self) -> None:
        """Override to implement stop logic."""
        pass

    def health_check(self) -> dict[str, Any]:
        """Override to implement health check."""
        return {"status": "ok", "healthy": True}

    def get_info(self) -> dict[str, Any]:
        with self._lock:
            return {
                "id": self.metadata.id,
                "name": self.metadata.name,
                "version": self.metadata.version,
                "status": self.status.value,
                "provides": self.metadata.provides,
                "dependencies": self.metadata.dependencies,
                "tags": self.metadata.tags,
                "load_time": self._load_time,
                "init_time": self._init_time,
                "error_count": self._error_count,
                "has_error": self._error is not None,
                "error": self._error,
            }

    def __repr__(self) -> str:
        return f"<Plugin {self.metadata.id} v{self.metadata.version} [{self.status.value}]>"
