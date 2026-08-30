"""High availability — failover, graceful degradation, circuit breaker for 99.9% uptime."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class CircuitState(Enum):
    CLOSED = "closed"  # Normal
    OPEN = "open"  # Failing
    HALF_OPEN = "half_open"  # Testing


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self._config = config or CircuitBreakerConfig()
        self._lock = threading.RLock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    def can_execute(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self._config.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    return True
                return False
            if self._state == CircuitState.HALF_OPEN:
                return self._half_open_calls < self._config.half_open_max_calls
        return False

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            else:
                self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
            elif self._failure_count >= self._config.failure_threshold:
                self._state = CircuitState.OPEN

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
            }


class FailoverManager:
    """Manage failover between primary and backup plugins."""

    def __init__(self):
        self._lock = threading.RLock()
        self._primaries: dict[str, Any] = {}
        self._backups: dict[str, Any] = {}
        self._active: dict[str, str] = {}  # plugin_id -> "primary" | "backup"
        self._failover_count: dict[str, int] = {}

    def register(self, plugin_id: str, primary: Any, backup: Any | None = None) -> None:
        with self._lock:
            self._primaries[plugin_id] = primary
            if backup:
                self._backups[plugin_id] = backup
            self._active[plugin_id] = "primary"

    def get_active(self, plugin_id: str) -> Any:
        with self._lock:
            active = self._active.get(plugin_id, "primary")
            if active == "primary":
                return self._primaries.get(plugin_id)
            return self._backups.get(plugin_id)

    def failover(self, plugin_id: str) -> bool:
        with self._lock:
            if plugin_id not in self._backups:
                return False
            self._active[plugin_id] = "backup"
            self._failover_count[plugin_id] = self._failover_count.get(plugin_id, 0) + 1
            return True

    def restore_primary(self, plugin_id: str) -> bool:
        with self._lock:
            if plugin_id not in self._primaries:
                return False
            self._active[plugin_id] = "primary"
            return True

    def get_failover_count(self, plugin_id: str) -> int:
        return self._failover_count.get(plugin_id, 0)

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_primaries": len(self._primaries),
                "total_backups": len(self._backups),
                "on_backup": sum(1 for v in self._active.values() if v == "backup"),
            }


class GracefulDegradation:
    """Graceful degradation when plugins fail."""

    def __init__(self):
        self._lock = threading.RLock()
        self._degradation_levels: dict[str, int] = {}  # plugin_id -> level (0=normal, >0=degraded)
        self._fallbacks: dict[str, Any] = {}
        self._disabled: set[str] = set()

    def degrade(self, plugin_id: str, level: int = 1) -> None:
        with self._lock:
            self._degradation_levels[plugin_id] = level

    def restore(self, plugin_id: str) -> None:
        with self._lock:
            self._degradation_levels.pop(plugin_id, None)

    def disable(self, plugin_id: str) -> None:
        with self._lock:
            self._disabled.add(plugin_id)

    def enable(self, plugin_id: str) -> None:
        with self._lock:
            self._disabled.discard(plugin_id)

    def is_available(self, plugin_id: str) -> bool:
        with self._lock:
            return plugin_id not in self._disabled

    def get_degradation_level(self, plugin_id: str) -> int:
        return self._degradation_levels.get(plugin_id, 0)

    def register_fallback(self, plugin_id: str, fallback: Any) -> None:
        with self._lock:
            self._fallbacks[plugin_id] = fallback

    def get_fallback(self, plugin_id: str) -> Any:
        with self._lock:
            return self._fallbacks.get(plugin_id)

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_degraded": len(self._degradation_levels),
                "total_disabled": len(self._disabled),
                "total_fallbacks": len(self._fallbacks),
            }


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "FailoverManager",
    "GracefulDegradation",
]
