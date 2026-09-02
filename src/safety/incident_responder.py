"""Incident Responder — Handle security incidents and recovery. Full API with backward compat."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable


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
    ESCALATED = "escalated"


class EscalationLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    L1_OPERATIONAL = "L1_operational"
    L2_TECHNICAL = "L2_technical"
    L3_MANAGEMENT = "L3_management"
    L4_EXTERNAL = "L4_external"


@dataclass
class EscalationRule:
    level: EscalationLevel
    action: str = ""
    target: str = ""
    enabled: bool = True
    handler: Optional[Callable] = None
    timeout_seconds: int = 0


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
    escalation_level: Optional[EscalationLevel] = None
    timeline: list[dict[str, Any]] = field(default_factory=list)

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
            "timeline": self.timeline,
        }


class IncidentResponder:
    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._escalation_rules: dict[IncidentLevel, list[EscalationRule]] = {}
        self._notification_log: list[dict[str, Any]] = []

    def default_escalation_rules(self) -> None:
        """Set up default escalation rules."""
        self._escalation_rules = {
            IncidentLevel.CRITICAL: [
                EscalationRule(level=EscalationLevel.L4_EXTERNAL, action="page_oncall", target="security-team"),
                EscalationRule(level=EscalationLevel.L3_MANAGEMENT, action="escalate_management", target="management"),
            ],
            IncidentLevel.HIGH: [
                EscalationRule(level=EscalationLevel.L3_MANAGEMENT, action="slack_alert", target="security-alerts"),
                EscalationRule(level=EscalationLevel.L2_TECHNICAL, action="page_tech", target="tech-team"),
            ],
            IncidentLevel.MEDIUM: [
                EscalationRule(level=EscalationLevel.L2_TECHNICAL, action="log_incident", target=""),
                EscalationRule(level=EscalationLevel.L1_OPERATIONAL, action="notify_ops", target="ops"),
            ],
            IncidentLevel.LOW: [
                EscalationRule(level=EscalationLevel.L1_OPERATIONAL, action="log_only", target=""),
            ],
        }

    def open_incident(self, title: str, description: str, level: IncidentLevel = IncidentLevel.MEDIUM, enforcement_result: Any = None) -> Incident:
        """Open a new incident."""
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        
        # Determine level from enforcement_result if provided
        if enforcement_result is not None and hasattr(enforcement_result, 'risk_level') and enforcement_result.risk_level:
            level_map = {
                "critical": IncidentLevel.CRITICAL,
                "high": IncidentLevel.HIGH,
                "medium": IncidentLevel.MEDIUM,
                "low": IncidentLevel.LOW,
            }
            rl = enforcement_result.risk_level
            level = level_map.get(rl.value if hasattr(rl, 'value') else str(rl), level)
        
        incident = Incident(
            incident_id=incident_id,
            title=title,
            description=description,
            level=level,
            status=IncidentStatus.DETECTED,
            enforcement_result=enforcement_result,
            severity=level,
        )
        incident.timeline.append({"status": "detected", "timestamp": time.time()})
        self._incidents[incident_id] = incident
        
        # Log notification
        self._notification_log.append({
            "incident_id": incident_id,
            "action": "opened",
            "level": level.value,
            "timestamp": time.time(),
        })
        
        return incident

    def handle_enforcement_result(self, result: Any) -> Optional[Incident]:
        """Handle an enforcement result by opening an incident if needed."""
        if result is None:
            return None
        
        # If action is BLOCK or ESCALATE, create an incident
        action_val = result.action.value if hasattr(result.action, 'value') else str(result.action)
        
        if action_val == "block" or action_val == "escalate":
            level_map = {
                "critical": IncidentLevel.CRITICAL,
                "high": IncidentLevel.HIGH,
                "medium": IncidentLevel.MEDIUM,
                "low": IncidentLevel.LOW,
            }
            rl = result.risk_level
            level = level_map.get(rl.value if hasattr(rl, 'value') else str(rl), IncidentLevel.MEDIUM)
            
            return self.open_incident(
                title=f"Enforcement action: {action_val}",
                description=result.reason if hasattr(result, 'reason') else "Enforcement triggered",
                level=level,
                enforcement_result=result,
            )
        
        return None

    def acknowledge(self, incident_id: str, by: str = "") -> Optional[Incident]:
        """Acknowledge an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.ACKNOWLEDGED
            incident.updated_at = time.time()
            incident.timeline.append({"status": "acknowledged", "by": by, "timestamp": time.time()})
            return incident
        return None

    def investigate(self, incident_id: str, notes: str = "") -> Optional[Incident]:
        """Set an incident to investigating status."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.INVESTIGATING
            incident.updated_at = time.time()
            incident.timeline.append({"status": "investigating", "notes": notes, "timestamp": time.time()})
            return incident
        return None

    def escalate(self, incident_id: str, to_level: Optional[EscalationLevel] = None) -> Optional[Incident]:
        """Escalate an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.updated_at = time.time()
            
            # Determine escalation level
            if to_level is not None:
                incident.escalation_level = to_level
            else:
                # Use default rules based on incident level
                rules = self._escalation_rules.get(incident.level, [])
                if rules:
                    incident.escalation_level = rules[0].level
                else:
                    incident.escalation_level = EscalationLevel.L1_OPERATIONAL
            
            incident.status = IncidentStatus.ESCALATED
            incident.timeline.append({"status": "escalated", "level": incident.escalation_level.value, "timestamp": time.time()})
            
            # Execute handler if exists
            rules = self._escalation_rules.get(incident.level, [])
            for rule in rules:
                if rule.handler:
                    rule.handler(incident)
            
            return incident
        return None

    def contain(self, incident_id: str, notes: str = "") -> Optional[Incident]:
        """Contain an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.CONTAINED
            incident.updated_at = time.time()
            incident.timeline.append({"status": "contained", "notes": notes, "timestamp": time.time()})
            return incident
        return None

    def resolve(self, incident_id: str, resolution: str = "") -> Optional[Incident]:
        """Resolve an incident (sets status to RESOLVED)."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.RESOLVED
            incident.resolution = resolution
            incident.resolved_at = time.time()
            incident.updated_at = time.time()
            incident.timeline.append({"status": "resolved", "resolution": resolution, "timestamp": time.time()})
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
        """Add an action to an incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            if not hasattr(incident, '_actions'):
                incident._actions = []
            incident._actions.append(action)

    def get_actions(self, incident_id: str) -> list:
        """Get actions for an incident."""
        incident = self._incidents.get(incident_id)
        if incident and hasattr(incident, '_actions'):
            return incident._actions
        return []

    def list_incidents(self, status: IncidentStatus | None = None) -> list[Incident]:
        """List incidents (backward compat)."""
        return self.list(status=status)

    def __len__(self) -> int:
        return len(self._incidents)

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
        all_rules = []
        for rules in self._escalation_rules.values():
            all_rules.extend(rules)
        return all_rules

    def add_escalation_rule(self, incident_level: IncidentLevel, rule: EscalationRule) -> None:
        """Add an escalation rule for a specific incident level."""
        if incident_level not in self._escalation_rules:
            self._escalation_rules[incident_level] = []
        self._escalation_rules[incident_level].append(rule)
