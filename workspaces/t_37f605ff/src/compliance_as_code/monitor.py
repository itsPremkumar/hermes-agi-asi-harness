"""Continuous compliance monitoring — scheduled checks and alerting."""

from __future__ import annotations

import json
import logging
import sched
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from compliance_as_code.engine import (
    ComplianceEngine,
    ComplianceFramework,
    ComplianceReport,
)

logger = logging.getLogger(__name__)


@dataclass
class MonitorConfig:
    """Configuration for continuous compliance monitoring."""
    framework: ComplianceFramework
    interval_seconds: int = 3600  # default: hourly
    alert_on_fail: bool = True
    alert_on_warning: bool = False
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitorResult:
    """Result of a single monitoring check."""
    check_id: str
    framework: ComplianceFramework
    timestamp: datetime
    report: ComplianceReport
    alerts_triggered: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "framework": self.framework.value,
            "timestamp": self.timestamp.isoformat(),
            "report": self.report.to_dict(),
            "alerts_triggered": self.alerts_triggered,
            "duration_seconds": self.duration_seconds,
        }


class ComplianceMonitor:
    """Continuous compliance monitoring with scheduling and alerting."""

    def __init__(self, engine: ComplianceEngine | None = None):
        self.engine = engine or ComplianceEngine()
        self._configs: list[MonitorConfig] = []
        self._history: list[MonitorResult] = []
        self._alert_handlers: list[Callable[[MonitorResult], None]] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._scheduler = sched.scheduler(time.time, time.sleep)

    def add_config(self, config: MonitorConfig) -> None:
        """Add a monitoring configuration."""
        self._configs.append(config)
        logger.info(
            "Added monitor for %s (every %ds)",
            config.framework.value,
            config.interval_seconds,
        )

    def on_alert(self, handler: Callable[[MonitorResult], None]) -> None:
        """Register an alert handler callback."""
        self._alert_handlers.append(handler)

    def run_once(
        self,
        framework: ComplianceFramework | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[MonitorResult]:
        """Run a single monitoring check."""
        results: list[MonitorResult] = []
        configs = self._configs
        if framework:
            configs = [c for c in configs if c.framework == framework]

        for config in configs:
            start = time.time()
            ctx = {**config.context, **(context or {})}
            report = self.engine.evaluate(config.framework, ctx)
            duration = time.time() - start

            alerts = self._check_alerts(config, report)
            result = MonitorResult(
                check_id=f"check-{config.framework.value}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                framework=config.framework,
                timestamp=datetime.now(timezone.utc),
                report=report,
                alerts_triggered=alerts,
                duration_seconds=round(duration, 3),
            )
            results.append(result)
            self._history.append(result)

            if alerts:
                for handler in self._alert_handlers:
                    try:
                        handler(result)
                    except Exception as exc:
                        logger.error("Alert handler error: %s", exc)

        return results

    def start(self) -> None:
        """Start continuous monitoring in a background thread."""
        if self._running:
            logger.warning("Monitor is already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Continuous compliance monitoring started")

    def stop(self) -> None:
        """Stop continuous monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Continuous compliance monitoring stopped")

    def get_history(
        self, framework: ComplianceFramework | None = None, limit: int = 100
    ) -> list[MonitorResult]:
        """Get monitoring history, optionally filtered by framework."""
        history = self._history
        if framework:
            history = [h for h in history if h.framework == framework]
        return history[-limit:]

    def _check_alerts(self, config: MonitorConfig, report: ComplianceReport) -> list[str]:
        """Check if alerts should be triggered based on report results."""
        alerts: list[str] = []

        if config.alert_on_fail and report.failed > 0:
            alerts.append(
                f"ALERT: {report.failed} control(s) failed for {config.framework.value}"
            )

        if config.alert_on_warning and report.warnings > 0:
            alerts.append(
                f"WARNING: {report.warnings} control(s) in warning state for {config.framework.value}"
            )

        return alerts

    def _run_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                self.run_once()
            except Exception as exc:
                logger.error("Monitoring check failed: %s", exc)

            # Sleep for the minimum interval
            if self._configs:
                min_interval = min(c.interval_seconds for c in self._configs)
            else:
                min_interval = 3600

            # Sleep in small increments so we can stop quickly
            for _ in range(min_interval):
                if not self._running:
                    break
                time.sleep(1)
