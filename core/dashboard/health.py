"""Health monitoring — track component health and uptime."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    component: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """Monitor health of system components."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._checks: dict[str, HealthCheck] = {}
        self._history: list[HealthCheck] = []

    def update(self, component: str, status: HealthStatus,
               latency_ms: float = 0.0, message: str = "") -> HealthCheck:
        check = HealthCheck(
            component=component,
            status=status,
            latency_ms=latency_ms,
            message=message,
        )
        self._checks[component] = check
        self._history.append(check)
        return check

    def get(self, component: str) -> HealthCheck | None:
        return self._checks.get(component)

    def get_all(self) -> dict[str, HealthCheck]:
        return dict(self._checks)

    def get_history(self, component: str, limit: int = 100) -> list[HealthCheck]:
        return [c for c in self._history if c.component == component][-limit:]

    def overall_status(self) -> HealthStatus:
        if not self._checks:
            return HealthStatus.UNKNOWN
        statuses = [c.status for c in self._checks.values()]
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def healthy_count(self) -> int:
        return sum(1 for c in self._checks.values() if c.status == HealthStatus.HEALTHY)

    def component_count(self) -> int:
        return len(self._checks)

    def uptime_ms(self) -> float:
        if not self._history:
            return 0.0
        return (time.time() - self._history[0].timestamp) * 1000

    def get_state(self) -> dict[str, Any]:
        return {
            "overall": self.overall_status().value,
            "components": self.component_count(),
            "healthy": self.healthy_count(),
            "uptime_ms": self.uptime_ms(),
        }
