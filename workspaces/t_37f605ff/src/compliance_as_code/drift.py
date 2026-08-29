"""Drift detection — identifies compliance violations by comparing current state to baseline."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DriftSeverity(str, Enum):
    """Severity of a detected drift."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class DriftType(str, Enum):
    """Type of drift detected."""
    CONFIGURATION = "CONFIGURATION"
    POLICY = "POLICY"
    ACCESS = "ACCESS"
    ENCRYPTION = "ENCRYPTION"
    NETWORK = "NETWORK"
    LOGGING = "LOGGING"


@dataclass
class DriftEvent:
    """A single compliance drift event."""
    event_id: str
    drift_type: DriftType
    severity: DriftSeverity
    control_id: str
    framework: str
    description: str
    expected_value: Any
    actual_value: Any
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    remediation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "control_id": self.control_id,
            "framework": self.framework,
            "description": self.description,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "detected_at": self.detected_at.isoformat(),
            "remediation": self.remediation,
            "metadata": self.metadata,
        }


@dataclass
class DriftReport:
    """Aggregated drift detection report."""
    report_id: str
    generated_at: datetime
    events: list[DriftEvent] = field(default_factory=list)

    @property
    def total_drifts(self) -> int:
        return len(self.events)

    @property
    def critical(self) -> int:
        return sum(1 for e in self.events if e.severity == DriftSeverity.CRITICAL)

    @property
    def high(self) -> int:
        return sum(1 for e in self.events if e.severity == DriftSeverity.HIGH)

    @property
    def by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.events:
            counts[e.drift_type.value] = counts.get(e.drift_type.value, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_drifts": self.total_drifts,
                "critical": self.critical,
                "high": self.high,
                "by_type": self.by_type,
            },
            "events": [e.to_dict() for e in self.events],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class DriftDetector:
    """Detects compliance drift by comparing current state against a baseline."""

    def __init__(self, baseline_path: str | Path | None = None):
        self.baseline_path = Path(baseline_path) if baseline_path else None
        self._baseline: dict[str, Any] = {}
        if self.baseline_path and self.baseline_path.exists():
            self._baseline = json.loads(self.baseline_path.read_text(encoding="utf-8"))

    def set_baseline(self, baseline: dict[str, Any]) -> None:
        """Set the compliance baseline to compare against."""
        self._baseline = baseline

    def save_baseline(self, path: str | Path | None = None) -> Path:
        """Persist the current baseline to disk."""
        target = Path(path) if path else self.baseline_path
        if not target:
            raise ValueError("No baseline path specified")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self._baseline, indent=2, default=str), encoding="utf-8")
        return target

    def detect_drift(
        self,
        current_state: dict[str, Any],
        framework: str = "SOC2",
    ) -> DriftReport:
        """Compare current state against baseline and return drift events."""
        report = DriftReport(
            report_id=f"drift-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            generated_at=datetime.now(timezone.utc),
        )

        for key, expected in self._baseline.items():
            actual = current_state.get(key)
            if actual != expected:
                event = self._classify_drift(key, expected, actual, framework)
                report.events.append(event)
                logger.warning(
                    "Drift detected: %s — expected=%s, actual=%s",
                    key, expected, actual,
                )

        return report

    def _classify_drift(
        self, key: str, expected: Any, actual: Any, framework: str
    ) -> DriftEvent:
        """Classify a drift event based on the key and values."""
        # Determine drift type and severity from key patterns
        key_lower = key.lower()
        if "encrypt" in key_lower or "tls" in key_lower or "cipher" in key_lower:
            drift_type = DriftType.ENCRYPTION
            severity = DriftSeverity.CRITICAL
        elif "firewall" in key_lower or "network" in key_lower or "acl" in key_lower:
            drift_type = DriftType.NETWORK
            severity = DriftSeverity.HIGH
        elif "rbac" in key_lower or "access" in key_lower or "permission" in key_lower:
            drift_type = DriftType.ACCESS
            severity = DriftSeverity.HIGH
        elif "log" in key_lower or "audit" in key_lower:
            drift_type = DriftType.LOGGING
            severity = DriftSeverity.MEDIUM
        elif "policy" in key_lower:
            drift_type = DriftType.POLICY
            severity = DriftSeverity.MEDIUM
        else:
            drift_type = DriftType.CONFIGURATION
            severity = DriftSeverity.LOW

        event_id = hashlib.sha256(
            f"{key}:{expected}:{actual}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]

        return DriftEvent(
            event_id=event_id,
            drift_type=drift_type,
            severity=severity,
            control_id=self._infer_control_id(key, framework),
            framework=framework,
            description=f"Configuration drift on '{key}': expected '{expected}', found '{actual}'",
            expected_value=expected,
            actual_value=actual,
            remediation=f"Restore '{key}' to expected value '{expected}'",
        )

    def _infer_control_id(self, key: str, framework: str) -> str:
        """Map a configuration key to a control ID."""
        mapping = {
            "rbac_enabled": "CC6.1",
            "mfa_enforced": "CC6.1",
            "encryption_at_rest": "CC6.7",
            "encryption_algorithm": "CC6.7",
            "firewall_enabled": "Req1",
            "default_deny_policy": "Req1",
            "tls_version": "Req4",
            "weak_protocols_disabled": "Req4",
            "unique_user_ids": "164.312(a)(1)",
            "ephi_encrypted": "164.312(a)(1)",
            "consent_records_maintained": "Art7",
            "erasure_procedure": "Art17",
        }
        control = mapping.get(key, "UNKNOWN")
        if framework != "SOC2" and control.startswith("CC"):
            return f"{framework}-{control}"
        return f"{framework}-{control}" if "-" not in control else control
