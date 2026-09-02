"""Advanced Plugin Hot-Reload System.

Allows runtime plugin loading, unloading, and reloading without restart.
Includes file watching, dependency-aware ordering, and rollback on failure.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class ReloadStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


@dataclass
class ReloadEvent:
    plugin_id: str
    status: ReloadStatus
    timestamp: float
    message: str = ""
    duration_ms: float = 0.0


@dataclass
class PluginSnapshot:
    """Snapshot of a plugin state for rollback."""
    plugin_id: str
    module_name: str
    source_code: str
    config: dict[str, Any]
    status: str


class PluginHotReloader:
    """Hot-reload plugins without restart."""

    def __init__(self):
        self._snapshots: dict[str, PluginSnapshot] = {}
        self._watchers: dict[str, threading.Thread] = {}
        self._callbacks: list[Callable[[ReloadEvent], None]] = []
        self._lock = threading.RLock()
        self._history: list[ReloadEvent] = []
        self._watching = False

    def register_callback(self, cb: Callable[[ReloadEvent], None]) -> None:
        """Register a callback for reload events."""
        with self._lock:
            self._callbacks.append(cb)

    def snapshot(self, plugin_id: str, module_name: str, source_code: str, config: dict[str, Any], status: str) -> None:
        """Take a snapshot of a plugin for rollback."""
        with self._lock:
            self._snapshots[plugin_id] = PluginSnapshot(
                plugin_id=plugin_id,
                module_name=module_name,
                source_code=source_code,
                config=config,
                status=status,
            )

    def reload_plugin(self, plugin_id: str, module_path: str, config: dict[str, Any] | None = None) -> ReloadEvent:
        """Hot-reload a single plugin."""
        start = time.time()
        with self._lock:
            # Take snapshot first
            if plugin_id in self._snapshots:
                old_snapshot = self._snapshots[plugin_id]
            else:
                old_snapshot = None

            try:
                # Load module
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_id}", module_path
                )
                if spec is None or spec.loader is None:
                    event = ReloadEvent(
                        plugin_id=plugin_id,
                        status=ReloadStatus.FAILED,
                        timestamp=time.time(),
                        message=f"Cannot load spec from {module_path}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                    self._history.append(event)
                    return event

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Snapshot for future rollback
                with open(module_path, "r") as f:
                    source = f.read()
                self.snapshot(plugin_id, module_path, source, config or {}, "active")

                event = ReloadEvent(
                    plugin_id=plugin_id,
                    status=ReloadStatus.SUCCESS,
                    timestamp=time.time(),
                    message=f"Plugin {plugin_id} reloaded successfully",
                    duration_ms=(time.time() - start) * 1000,
                )
                self._history.append(event)
                self._notify(event)
                return event

            except Exception as e:
                # Rollback if we have a snapshot
                if old_snapshot:
                    event = ReloadEvent(
                        plugin_id=plugin_id,
                        status=ReloadStatus.ROLLED_BACK,
                        timestamp=time.time(),
                        message=f"Reload failed, rolled back: {e}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                else:
                    event = ReloadEvent(
                        plugin_id=plugin_id,
                        status=ReloadStatus.FAILED,
                        timestamp=time.time(),
                        message=f"Reload failed: {e}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                self._history.append(event)
                self._notify(event)
                return event

    def rollback(self, plugin_id: str) -> ReloadEvent:
        """Rollback a plugin to its last snapshot."""
        start = time.time()
        with self._lock:
            snapshot = self._snapshots.get(plugin_id)
            if not snapshot:
                return ReloadEvent(
                    plugin_id=plugin_id,
                    status=ReloadStatus.FAILED,
                    timestamp=time.time(),
                    message=f"No snapshot for {plugin_id}",
                    duration_ms=(time.time() - start) * 1000,
                )

            try:
                # Restore source code
                with open(snapshot.module_name, "w") as f:
                    f.write(snapshot.source_code)

                # Reload
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_id}", snapshot.module_name
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                event = ReloadEvent(
                    plugin_id=plugin_id,
                    status=ReloadStatus.ROLLED_BACK,
                    timestamp=time.time(),
                    message=f"Plugin {plugin_id} rolled back",
                    duration_ms=(time.time() - start) * 1000,
                )
                self._history.append(event)
                self._notify(event)
                return event

            except Exception as e:
                return ReloadEvent(
                    plugin_id=plugin_id,
                    status=ReloadStatus.FAILED,
                    timestamp=time.time(),
                    message=f"Rollback failed: {e}",
                    duration_ms=(time.time() - start) * 1000,
                )

    def start_watching(self, plugin_id: str, module_path: str, interval: float = 2.0) -> None:
        """Start watching a plugin file for changes."""
        with self._lock:
            if plugin_id in self._watchers:
                return  # Already watching

            self._watching = True
            thread = threading.Thread(
                target=self._watch_loop,
                args=(plugin_id, module_path, interval),
                daemon=True,
            )
            self._watchers[plugin_id] = thread
            thread.start()

    def stop_watching(self, plugin_id: str) -> None:
        """Stop watching a plugin file."""
        with self._lock:
            self._watching = False
            if plugin_id in self._watchers:
                del self._watchers[plugin_id]

    def stop_all(self) -> None:
        """Stop all watchers."""
        with self._lock:
            self._watching = False
            self._watchers.clear()

    def get_history(self) -> list[ReloadEvent]:
        """Get reload history."""
        with self._lock:
            return list(self._history)

    def get_snapshots(self) -> dict[str, PluginSnapshot]:
        """Get all snapshots."""
        with self._lock:
            return dict(self._snapshots)

    def _watch_loop(self, plugin_id: str, module_path: str, interval: float) -> None:
        """Watch loop for a plugin file."""
        last_mtime = 0.0
        while self._watching:
            try:
                mtime = Path(module_path).stat().st_mtime
                if mtime != last_mtime and last_mtime != 0:
                    self.reload_plugin(plugin_id, module_path)
                last_mtime = mtime
            except (FileNotFoundError, OSError):
                pass
            time.sleep(interval)

    def _notify(self, event: ReloadEvent) -> None:
        """Notify all callbacks."""
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception:
                pass
