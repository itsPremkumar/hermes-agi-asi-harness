"""
Observability Dashboard Plugin — Real-Time System Monitoring

Tracks: plugin health, resource usage, mission status, errors,
performance metrics, alerts. Provides unified view of system state.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import deque


@dataclass
class MetricPoint:
    name: str
    value: float
    unit: str = ""
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    severity: str
    source: str
    message: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }


class ObservabilityDashboard:
    """System observability and monitoring."""

    def __init__(self, max_points: int = 1000):
        self._metrics: Dict[str, deque] = {}
        self._alerts: List[Alert] = []
        self._max_points = max_points
        self._plugin_health: Dict[str, Dict[str, Any]] = {}
        self._start_time = time.time()

    def record_metric(self, name: str, value: float, unit: str = "",
                      tags: Dict[str, str] = None):
        """Record a metric data point."""
        point = MetricPoint(
            name=name,
            value=value,
            unit=unit,
            tags=tags or {},
        )
        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=self._max_points)
        self._metrics[name].append(point)

    def get_metric_history(self, name: str, limit: int = 100) -> List[MetricPoint]:
        if name not in self._metrics:
            return []
        return list(self._metrics[name])[-limit:]

    def get_metric_stats(self, name: str) -> Dict[str, float]:
        if name not in self._metrics or not self._metrics[name]:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "current": 0}
        values = [p.value for p in self._metrics[name]]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "current": values[-1],
        }

    def register_plugin_health(self, plugin_name: str, health: Dict[str, Any]):
        self._plugin_health[plugin_name] = {
            **health,
            "last_check": time.time(),
        }

    def get_plugin_health(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        return self._plugin_health.get(plugin_name)

    def get_all_plugin_health(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._plugin_health)

    def raise_alert(self, severity: str, source: str, message: str):
        alert = Alert(severity=severity, source=source, message=message)
        self._alerts.append(alert)

    def get_active_alerts(self, limit: int = 20) -> List[Alert]:
        return [a for a in reversed(self._alerts) if not a.acknowledged][:limit]

    def acknowledge_alert(self, index: int):
        if 0 <= index < len(self._alerts):
            self._alerts[index].acknowledged = True

    def get_dashboard_summary(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time
        healthy_plugins = sum(1 for h in self._plugin_health.values()
                             if h.get("status") == "healthy")
        total_plugins = len(self._plugin_health)
        return {
            "uptime_seconds": round(uptime, 1),
            "total_metrics": len(self._metrics),
            "total_data_points": sum(len(m) for m in self._metrics.values()),
            "plugins_healthy": healthy_plugins,
            "plugins_total": total_plugins,
            "active_alerts": len([a for a in self._alerts if not a.acknowledged]),
            "total_alerts": len(self._alerts),
        }


class ObservabilityDashboardPlugin:
    def __init__(self):
        self.engine = ObservabilityDashboard()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "summary": self.engine.get_dashboard_summary(),
        }


async def create(kernel=None):
    plugin = ObservabilityDashboardPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
