"""Health monitor — monitor plugin health and report status."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    plugin_id: str
    status: HealthStatus
    message: str = ""
    checks: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY


class HealthMonitor:
    """Monitors plugin health and aggregates status."""

    def __init__(self):
        self._lock = threading.RLock()
        self._results: dict[str, HealthCheckResult] = {}
        self._history: dict[str, list[HealthCheckResult]] = {}
        self._max_history = 10

    def check_health(self, plugin) -> HealthCheckResult:
        """Run a health check on a plugin."""
        try:
            result_data = plugin.health_check()
            if isinstance(result_data, dict):
                healthy = result_data.get("healthy", result_data.get("status") == "ok")
                message = result_data.get("message", "")
                checks = {k: v for k, v in result_data.items() if k not in ("healthy", "status", "message")}
            else:
                healthy = True
                message = ""
                checks = {}
        except Exception as e:
            healthy = False
            message = str(e)
            checks = {}

        status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
        result = HealthCheckResult(
            plugin_id=plugin.metadata.id,
            status=status,
            message=message,
            checks=checks,
        )

        with self._lock:
            self._results[plugin.metadata.id] = result
            self._history.setdefault(plugin.metadata.id, []).append(result)
            # Trim history
            if len(self._history[plugin.metadata.id]) > self._max_history:
                self._history[plugin.metadata.id] = self._history[plugin.metadata.id][-self._max_history:]

        return result

    def get_status(self, plugin_id: str) -> Optional[HealthCheckResult]:
        with self._lock:
            return self._results.get(plugin_id)

    def get_history(self, plugin_id: str) -> list[HealthCheckResult]:
        with self._lock:
            return list(self._history.get(plugin_id, []))

    def get_all_statuses(self) -> dict[str, HealthCheckResult]:
        with self._lock:
            return dict(self._results)

    def get_healthy(self) -> list[str]:
        with self._lock:
            return [pid for pid, r in self._results.items() if r.is_healthy]

    def get_unhealthy(self) -> list[str]:
        with self._lock:
            return [pid for pid, r in self._results.items() if not r.is_healthy]

    def get_overall_status(self) -> HealthStatus:
        with self._lock:
            if not self._results:
                return HealthStatus.UNKNOWN
            statuses = [r.status for r in self._results.values()]
            if all(s == HealthStatus.HEALTHY for s in statuses):
                return HealthStatus.HEALTHY
            if any(s == HealthStatus.UNHEALTHY for s in statuses):
                return HealthStatus.UNHEALTHY
            return HealthStatus.DEGRADED

    def clear(self) -> None:
        with self._lock:
            self._results.clear()
            self._history.clear()
