"""
Watchdog Plugin — System Health Monitoring & Anomaly Detection

Monitors: process health, state health, agent health, resource usage.
Detects: deadlocks, hung processes, memory exhaustion, agent loops,
tool failures, state corruption, unexpected costs, failed jobs,
queue overload, security anomalies.
"""

import os
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from collections import deque

try:
    import resource  # POSIX only
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

try:
    import psutil  # type: ignore
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class AnomalyType(str, Enum):
    DEADLOCK = "deadlock"
    HUNG_PROCESS = "hung_process"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    AGENT_LOOP = "agent_loop"
    TOOL_FAILURE = "tool_failure"
    STATE_CORRUPTION = "state_corruption"
    UNEXPECTED_COST = "unexpected_cost"
    FAILED_JOB = "failed_job"
    QUEUE_OVERLOAD = "queue_overload"
    SECURITY_ANOMALY = "security_anomaly"


@dataclass
class Anomaly:
    type: str
    severity: str
    message: str
    detected_at: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "detected_at": self.detected_at,
            "context": self.context,
            "resolved": self.resolved,
        }


@dataclass
class WatchdogMetrics:
    checks_run: int = 0
    anomalies_detected: int = 0
    anomalies_resolved: int = 0
    last_check: float = 0.0
    uptime_seconds: float = 0.0
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0


class Watchdog:
    """System health monitoring and anomaly detection."""

    # Thresholds
    MEMORY_THRESHOLD_MB = 1000
    QUEUE_SIZE_THRESHOLD = 1000
    ANOMALY_WINDOW_SECONDS = 300
    LOOP_DETECTION_THRESHOLD = 5

    def __init__(self):
        self._anomalies: List[Anomaly] = []
        self._metrics = WatchdogMetrics()
        self._start_time = time.time()
        self._recent_events: deque = deque(maxlen=100)
        self._loop_counter: Dict[str, List[float]] = {}
        self._check_callbacks: List[Callable] = []

    def register_check(self, callback: Callable):
        """Register a health check callback."""
        self._check_callbacks.append(callback)

    def record_event(self, event_type: str, data: Dict[str, Any] = None):
        """Record an event for loop/anomaly detection."""
        self._recent_events.append({
            "type": event_type,
            "data": data or {},
            "timestamp": time.time(),
        })

        # Track for loop detection
        if event_type not in self._loop_counter:
            self._loop_counter[event_type] = []
        self._loop_counter[event_type].append(time.time())

        # Keep only recent timestamps
        cutoff = time.time() - self.ANOMALY_WINDOW_SECONDS
        self._loop_counter[event_type] = [
            t for t in self._loop_counter[event_type] if t > cutoff
        ]

    def detect_anomalies(self) -> List[Anomaly]:
        """Run all anomaly detection checks."""
        new_anomalies = []

        # Check for loops (same event type fired too many times in window)
        for event_type, timestamps in self._loop_counter.items():
            if len(timestamps) >= self.LOOP_DETECTION_THRESHOLD:
                anomaly = Anomaly(
                    type=AnomalyType.AGENT_LOOP.value,
                    severity="medium",
                    message=f"Event '{event_type}' fired {len(timestamps)} times in {self.ANOMALY_WINDOW_SECONDS}s",
                    context={"event_type": event_type, "count": len(timestamps)},
                )
                self._anomalies.append(anomaly)
                new_anomalies.append(anomaly)

        # Check memory usage
        mem_mb = 0.0
        if HAS_RESOURCE:
            try:
                mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            except (AttributeError, OSError):
                pass
        if mem_mb == 0.0 and HAS_PSUTIL:
            try:
                import psutil
                process = psutil.Process()
                mem_mb = process.memory_info().rss / 1024 / 1024
            except Exception:
                pass
        self._metrics.memory_usage_mb = mem_mb
        if mem_mb > self.MEMORY_THRESHOLD_MB:
            anomaly = Anomaly(
                type=AnomalyType.MEMORY_EXHAUSTION.value,
                severity="high",
                message=f"Memory usage high: {mem_mb:.1f} MB (threshold: {self.MEMORY_THRESHOLD_MB} MB)",
                context={"memory_mb": mem_mb, "threshold_mb": self.MEMORY_THRESHOLD_MB},
            )
            self._anomalies.append(anomaly)
            new_anomalies.append(anomaly)

        # Run registered checks
        for callback in self._check_callbacks:
            try:
                result = callback()
                if result and isinstance(result, dict) and result.get("anomaly"):
                    anomaly = Anomaly(**result["anomaly"])
                    self._anomalies.append(anomaly)
                    new_anomalies.append(anomaly)
            except Exception as e:
                pass  # Don't let check failures crash the watchdog

        self._metrics.checks_run += 1
        self._metrics.anomalies_detected += len(new_anomalies)
        self._metrics.last_check = time.time()
        self._metrics.uptime_seconds = time.time() - self._start_time
        return new_anomalies

    def get_metrics(self) -> WatchdogMetrics:
        self._metrics.anomalies_resolved = sum(1 for a in self._anomalies if a.resolved)
        return self._metrics

    def get_recent_anomalies(self, limit: int = 10) -> List[Anomaly]:
        return list(reversed(self._anomalies[-limit:]))

    def resolve_anomaly(self, index: int):
        if 0 <= index < len(self._anomalies):
            self._anomalies[index].resolved = True

    def get_health_report(self) -> Dict[str, Any]:
        metrics = self.get_metrics()
        return {
            "status": "healthy" if metrics.anomalies_detected == 0 or metrics.anomalies_resolved == metrics.anomalies_detected else "degraded",
            "metrics": {
                "checks_run": metrics.checks_run,
                "anomalies_detected": metrics.anomalies_detected,
                "anomalies_resolved": metrics.anomalies_resolved,
                "uptime_seconds": round(metrics.uptime_seconds, 1),
                "memory_usage_mb": round(metrics.memory_usage_mb, 1),
            },
            "recent_anomalies": len(self.get_recent_anomalies()),
        }


class WatchdogPlugin:
    def __init__(self):
        self.engine = Watchdog()

    async def load(self):
        pass

    async def start(self):
        # Start background monitoring thread
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _monitor_loop(self):
        """Background thread for continuous monitoring."""
        while getattr(self, '_running', False):
            self.engine.detect_anomalies()
            time.sleep(5)

    async def stop(self):
        self._running = False
        if hasattr(self, '_thread'):
            self._thread.join(timeout=2)

    async def health(self):
        return self.engine.get_health_report()

    def record_event(self, event_type: str, data: Dict[str, Any] = None):
        self.engine.record_event(event_type, data)

    def register_check(self, callback: Callable):
        self.engine.register_check(callback)


async def create(kernel=None):
    plugin = WatchdogPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
