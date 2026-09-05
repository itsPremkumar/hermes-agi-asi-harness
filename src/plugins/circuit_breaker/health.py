"""Health Monitor for ASI Cognitive Architecture.

Per-plane heartbeat tracking, latency percentile calculation (P50, P95, P99),
error rate measurement, and health status endpoint.
"""

from __future__ import annotations

import time
from typing import Any

from . import CircuitBreakerPlugin, CircuitState


class HealthMonitor:
    """Monitors health of all cognitive planes."""

    def __init__(self, circuit_breaker: CircuitBreakerPlugin):
        self._cb = circuit_breaker

    def get_plane_health(self, plane_name: str) -> dict[str, Any]:
        """Get comprehensive health for a single plane."""
        return self._cb.get_plane_health(plane_name)

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        """Get health for all registered planes."""
        return self._cb.get_all_health()

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health summary."""
        return self._cb.get_overall_health()

    def is_healthy(self, plane_name: str) -> bool:
        """Check if a specific plane is healthy."""
        health = self._cb.get_plane_health(plane_name)
        return (
            health["circuit_state"] == CircuitState.CLOSED.value
            and health["error_rate"] < 0.3
            and health["consecutive_failures"] < 3
        )

    def needs_attention(self, plane_name: str) -> bool:
        """Check if a plane needs attention (half-open or elevated errors)."""
        health = self._cb.get_plane_health(plane_name)
        return health["circuit_state"] in (
            CircuitState.OPEN.value,
            CircuitState.HALF_OPEN.value,
        ) or health["error_rate"] > 0.5

    def get_status_report(self) -> dict[str, Any]:
        """Generate a full status report."""
        all_health = self._cb.get_all_health()
        system = self._cb.get_overall_health()

        # Categorize planes
        healthy = []
        degraded = []
        critical = []

        for name, health in all_health.items():
            if health["circuit_state"] == CircuitState.OPEN.value:
                critical.append(name)
            elif health["circuit_state"] == CircuitState.HALF_OPEN.value:
                degraded.append(name)
            elif health["error_rate"] > 0.3:
                degraded.append(name)
            else:
                healthy.append(name)

        return {
            "system_status": system["status"],
            "total_planes": system["planes"],
            "healthy_planes": healthy,
            "degraded_planes": degraded,
            "critical_planes": critical,
            "open_circuits": system["open_circuits"],
            "half_open_circuits": system["half_open_circuits"],
            "closed_circuits": system["closed_circuits"],
            "planes": all_health,
            "timestamp": time.time(),
        }

    def get_latency_summary(self, plane_name: str | None = None) -> dict[str, Any]:
        """Get latency summary for a plane or all planes."""
        if plane_name:
            health = self._cb.get_plane_health(plane_name)
            return {
                "plane": plane_name,
                "p50_ms": health["p50_latency_ms"],
                "p95_ms": health["p95_latency_ms"],
                "p99_ms": health["p99_latency_ms"],
                "avg_ms": health["average_latency_ms"],
            }

        # All planes
        all_health = self._cb.get_all_health()
        return {
            name: {
                "p50_ms": h["p50_latency_ms"],
                "p95_ms": h["p95_latency_ms"],
                "p99_ms": h["p99_latency_ms"],
                "avg_ms": h["average_latency_ms"],
            }
            for name, h in all_health.items()
        }

    def get_error_summary(self) -> dict[str, Any]:
        """Get error rate summary across all planes."""
        all_health = self._cb.get_all_health()
        return {
            name: {
                "error_rate": h["error_rate"],
                "errors_per_minute": h["errors_per_minute"],
                "total_failures": h["failed_calls"],
                "total_timeouts": h["timeout_calls"],
                "last_error": h["last_error"],
            }
            for name, h in all_health.items()
        }
