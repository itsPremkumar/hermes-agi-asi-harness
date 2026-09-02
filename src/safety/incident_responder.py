"""Incident Responder — Handle security incidents and recovery. Full API with backward compat."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class IncidentLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Alias for backward compatibility with older tests
IncidentSeverity = IncidentLevel


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EscalationLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EscalationRule:
    level: EscalationLevel
    action: str
    target: str = ""
    enabled: bool = True


@dataclass
class Incident:
    incident_id: str
    title: str
    description: str
    level: IncidentLevel = IncidentLevel.MEDIUM
    status: IncidentStatus = IncidentStatus.DETECTED
    enforcement_result: Any = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    resolution: str | None = None
    severity: IncidentLevel = IncidentLevel.MEDIUM  # Backward compat

    def __eq__(self, other):
        if isinstance(other, Incident):
            return self.incident_id == other.incident_id
        return False

    def __hash__(self):
        return hash(self.incident_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "level": self.level.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution,
        }


class IncidentResponder:
    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._escalation_rules: list[EscalationRule] = []
        self._notification_log: list[dict[str, Any]] = []

    def default_escalation_rules(self) -> None:
        """Set up default escalation rules."""
        self._escalation_rules = [
            EscalationRule(level=EscalationLevel.CRITICAL, action="page_oncall", target="security-team"),
            EscalationRule(level=EscalationLevel.HIGH, action="slack_alert", target="security-alerts"),
            EscalationRule(level=EscalationLevel.MEDIUM, action="log_incident", target=""),
            EscalationRule(level=EscalationLevel.LOW, action="log_only", target=""),
        ]

    def open_incident(self, title: str, description: str, level: IncidentLevel = IncidentLevel.MEDIUM, enforcement_result: Any = None) -> Incident:
        """Open a new incident."""
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        incident = Incident(
            incident_id=incident_id,
            title=title,
            description=description,
            level=level,
            status=IncidentStatus.DETECTED,
            enforcement_result=enforcement_result,
            severity=level,
        )
        self._incidents[incident_id] = incident
        return incident

    def handle_enforcement_result(self, result: Any) -> Optional[Incident]:
        """Handle an enforcement result by opening an incident if needed."""
        if result is None:
            return None
        if hasattr(result, 'allowed') and result.allowed:
            return None
        if hasattr(result, 'risk_level') and result.risk_level:
            level_map = {
                "critical": IncidentLevel.CRITICAL,
                "high": IncidentLevel.HIGH,
                "medium": IncidentLevel.MEDIUM,
                "low": IncidentLevel.LOW,
            }
            level = level_map.get(result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level), IncidentLevel.MEDIUM)
        else:
            level = IncidentLevel.MEDIUM
        return self.open_incident(
            title=f"Enforcement action: {result.action.value if hasattr(result.action, 'value') else result.action}",
            description=result.reason if hasattr(result, 'reason') else "Enforcement triggered",
            level=level,
            enforcement_result=result,
        )

    def acknowledge(self, incident_id: str, by: str = "") -> Optional[Incident]:
        """Acknowledge an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.ACKNOWLEDGED
            incident.updated_at = time.time()
            return incident
        return None

    def investigate(self, incident_id: str, notes: str = "") -> Optional[Incident]:
        """Set an incident to investigating status."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.INVESTIGATING
            incident.updated_at = time.time()
            return incident
        return None

    def escalate(self, incident_id: str, level: EscalationLevel = EscalationLevel.HIGH) -> Optional[Incident]:
        """Escalate an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.updated_at = time.time()
            for rule in self._escalation_rules:
                if rule.level == level and rule.enabled:
                    self._notification_log.append({
                        "incident_id": incident_id,
                        "action": rule.action,
                        "target": rule.target,
                        "timestamp": time.time(),
                    })
            return incident
        return None

    def contain(self, incident_id: str, notes: str = "") -> Optional[Incident]:
        """Contain an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.CONTAINED
            incident.updated_at = time.time()
            return incident
        return None

    def resolve(self, incident_id: str, resolution: str = "") -> Optional[Incident]:
        """Resolve an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.RESOLVED
            incident.resolution = resolution
            incident.resolved_at = time.time()
            incident.updated_at = time.time()
            return incident
        return None

    def close(self, incident_id: str) -> Optional[Incident]:
        """Close an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.CLOSED
            incident.updated_at = time.time()
            return incident
        return None

    def get(self, incident_id: str) -> Optional[Incident]:
        """Get an incident by ID."""
        return self._incidents.get(incident_id)

    def list(self, status: IncidentStatus | None = None) -> list[Incident]:
        """List incidents, optionally filtered by status."""
        incidents = list(self._incidents.values())
        if status:
            incidents = [i for i in incidents if i.status == status]
        return incidents

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get an incident by ID (backward compat)."""
        return self._incidents.get(incident_id)

    def create_incident(self, title: str, severity: Any = None, description: str = "") -> str:
        """Create an incident (backward compat)."""
        level = IncidentLevel.MEDIUM
        if severity:
            if isinstance(severity, IncidentLevel):
                level = severity
            elif isinstance(severity, str):
                level_map = {"critical": IncidentLevel.CRITICAL, "high": IncidentLevel.HIGH, "medium": IncidentLevel.MEDIUM, "low": IncidentLevel.LOW}
                level = level_map.get(severity.lower(), IncidentLevel.MEDIUM)
        incident = self.open_incident(title=title, description=description, level=level)
        return incident.incident_id

    def update_status(self, incident_id: str, status: IncidentStatus) -> bool:
        """Update incident status (backward compat)."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return False
        incident.status = status
        incident.updated_at = time.time()
        return True

    def add_action(self, incident_id: str, action: str) -> None:
        """Add an action to an incident (backward compat - no-op)."""
        pass

    def get_actions(self, incident_id: str) -> list:
        """Get actions for an incident (backward compat)."""
        return []

    def list_incidents(self, status: IncidentStatus | None = None) -> list[Incident]:
        """List incidents (backward compat)."""
        return self.list(status=status)

    def __len__(self) -> int:
        return len(self._incidents)

    @property
    def active_incidents(self) -> list[Incident]:
        """Get active (non-resolved, non-closed) incidents."""
        return [i for i in self._incidents.values() if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)]

    @property
    def notification_log(self) -> list[dict[str, Any]]:
        """Get notification log."""
        return self._notification_log

    def by_level(self, level: IncidentLevel) -> list[Incident]:
        """Get incidents by level."""
        return [i for i in self._incidents.values() if i.level == level]

    def by_status(self, status: IncidentStatus) -> list[Incident]:
        """Get incidents by status."""
        return [i for i in self._incidents.values() if i.status == status]

    def escalation_rules(self) -> list[EscalationRule]:
        """Get escalation rules."""
        return self._escalation_rules

    def add_escalation_rule(self, rule: EscalationRule) -> None:
        """Add an escalation rule."""
        self._escalation_rules.append(rule)
