"""Alerting on quality threshold breaches."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from qualitywatch.models import CheckResult, Severity, Status


class Alert:
    """A single quality alert."""

    def __init__(
        self,
        rule_name: str,
        message: str,
        severity: Severity,
        score: float,
        threshold: float,
        timestamp: datetime | None = None,
    ) -> None:
        self.rule_name = rule_name
        self.message = message
        self.severity = severity
        self.score = score
        self.threshold = threshold
        self.timestamp = timestamp or datetime.now()
        self.resolved = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "message": self.message,
            "severity": self.severity.value,
            "score": self.score,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
        }


class AlertManager:
    """Monitors quality score and fires alerts when thresholds breach."""

    def __init__(self, threshold: float = 80.0, on_alert: Any = None) -> None:
        self.threshold = threshold
        self.on_alert = on_alert            # callback(rule_name, alert)
        self.alerts: list[Alert] = []
        self._last_score: float | None = None

    def evaluate(self, score: float, results: list[CheckResult]) -> list[Alert] | None:
        """Evaluate score against threshold. Returns fired alerts or None."""
        self._last_score = score
        fired = []
        for r in results:
            if r.status.value == "fail" and r.severity == Severity.ERROR:
                alert = Alert(
                    rule_name=r.rule_name,
                    message=r.message,
                    severity=r.severity,
                    score=score,
                    threshold=self.threshold,
                )
                self.alerts.append(alert)
                fired.append(alert)
                if self.on_alert:
                    self.on_alert(r.rule_name, alert)
        return fired if fired else None

    @property
    def breached(self) -> bool:
        return self._last_score is not None and self._last_score < self.threshold