<<<<<<< HEAD
"""Incident Responder — respond to safety incidents and manage escalation paths."""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable, Protocol

from src.safety.threat_modeler import Threat
from src.safety.risk_assessor import RiskAssessment, RiskLevel
from src.safety.safety_enforcer import EnforcementResult


class IncidentType(Enum):
    """Types of safety incidents."""

    THREAT_DETECTED = "threat_detected"
    POLICY_VIOLATION = "policy_violation"
    BLOCK_ENFORCEMENT = "block_enforcement"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SYSTEM_COMPROMISE = "system_compromise"
    DATA_BREACH = "data_breach"
    RESOURCE_ABUSE = "resource_abuse"
    CUSTOM = "custom"


class IncidentSeverity(Enum):
    """Severity levels for incidents."""
=======
"""Incident Responder — respond to safety incidents and escalation paths.

Part of the Advanced Safety Module. When an operation is blocked or an
anomaly is detected, the :class:`IncidentResponder` opens an :class:`Incident`,
routes it through escalation levels, tracks status transitions, and can
invoke user-supplied handlers at each stage.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from safety.safety_enforcer import EnforcementResult, PolicyAction

logger = logging.getLogger(__name__)

__all__ = [
    "EscalationLevel",
    "EscalationRule",
    "Incident",
    "IncidentLevel",
    "IncidentResponder",
    "IncidentStatus",
]


class IncidentLevel(Enum):
    """Severity of a safety incident."""
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
<<<<<<< HEAD
    LOW = "low"
    INFO = "info"


class EscalationAction(Enum):
    """Actions to take during incident escalation."""

    LOG = "log"
    ALERT = "alert"
    NOTIFY = "notify"
    ISOLATE = "isolate"
    SHUTDOWN = "shutdown"
    BLOCK_IP = "block_ip"
    SUSPEND_ACCOUNT = "suspend_account"
    CUSTOM = "custom"


# Mapping from IncidentSeverity to escalation actions.
_SEVERITY_ESCALATION: dict[IncidentSeverity, list[EscalationAction]] = {
    IncidentSeverity.CRITICAL: [
        EscalationAction.LOG,
        EscalationAction.ALERT,
        EscalationAction.NOTIFY,
        EscalationAction.ISOLATE,
        EscalationAction.SHUTDOWN,
    ],
    IncidentSeverity.HIGH: [
        EscalationAction.LOG,
        EscalationAction.ALERT,
        EscalationAction.NOTIFY,
        EscalationAction.ISOLATE,
    ],
    IncidentSeverity.MEDIUM: [
        EscalationAction.LOG,
        EscalationAction.ALERT,
        EscalationAction.NOTIFY,
    ],
    IncidentSeverity.LOW: [
        EscalationAction.LOG,
        EscalationAction.ALERT,
    ],
    IncidentSeverity.INFO: [
        EscalationAction.LOG,
    ],
}
=======
    LOW = "info"


class IncidentStatus(Enum):
    """Lifecycle status of an incident."""

    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EscalationLevel(Enum):
    """Escalation tiers for incident routing."""

    L1_OPERATIONAL = "l1_operational"      # team lead
    L2_SECURITY = "l2_security"            # security on-call
    L3_MANAGEMENT = "l3_management"        # director / CTO
    L4_EXTERNAL = "l4_external"            # regulator / board


@dataclass
class EscalationRule:
    """A rule mapping an incident to an escalation level + handler."""

    level: EscalationLevel
    handler: Callable[[Incident], Any] | None = None
    timeout_seconds: float = 300.0
    description: str = ""
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109


@dataclass
class Incident:
<<<<<<< HEAD
    """Represents a safety incident."""

    id: str
    incident_type: IncidentType
    severity: IncidentSeverity
    title: str
    description: str
    threats: list[Threat] = field(default_factory=list)
    risk_assessments: list[RiskAssessment] = field(default_factory=list)
    enforcement_result: Optional[EnforcementResult] = None
    escalation_level: int = 0
    escalation_actions: list[EscalationAction] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved: bool = False
    resolver: str = ""
    resolution_notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_critical(self) -> bool:
        return self.severity == IncidentSeverity.CRITICAL

    @property
    def age_seconds(self) -> float:
        end = self.resolved_at or time.time()
        return end - self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "incident_type": self.incident_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "threats": [t.name for t in self.threats],
            "risk_levels": [r.risk_level.value for r in self.risk_assessments],
            "enforcement_allowed": (
                self.enforcement_result.allowed
                if self.enforcement_result
                else None
            ),
            "escalation_level": self.escalation_level,
            "escalation_actions": [a.value for a in self.escalation_actions],
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolved": self.resolved,
            "age_seconds": self.age_seconds,
            "metadata": self.metadata,
        }


# ------------------------------------------------------------------
# Escalation responder protocol (allows pluggable responders)
# ------------------------------------------------------------------

class EscalationHandler(Protocol):
    def handle(self, incident: Incident, action: EscalationAction) -> Any: ...


class LoggingEscalationHandler:
    """Default escalation handler that logs actions."""

    def __init__(self):
        self.actions_taken: list[tuple[str, str, EscalationAction]] = []

    def handle(self, incident: Incident, action: EscalationAction) -> str:
        msg = (
            f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] "
            f"Incident {incident.id} ({incident.severity.value}): "
            f"action={action.value} type={incident.incident_type.value}"
        )
        self.actions_taken.append((incident.id, incident.title, action))
        return msg


class IncidentResponder:
    """Respond to safety incidents and manage escalation paths."""

    def __init__(self):
        self._lock = threading.RLock()
        self._incidents: dict[str, Incident] = {}
        self._counter = 0
        self._escalation_handler: EscalationHandler = LoggingEscalationHandler()
        self._escalation_callbacks: dict[EscalationAction, list[Callable]] = {
            a: [] for a in EscalationAction
        }
        self._suppression_rules: list[Callable[[Incident], bool]] = []
        self._stats: dict[str, int] = {
            "total_incidents": 0,
            "critical_incidents": 0,
            "high_incidents": 0,
            "resolved_incidents": 0,
            "total_escalations": 0,
        }

    # ------------------------------------------------------------------
    # Incident creation / management
    # ------------------------------------------------------------------

    def handle_threat(
        self,
        threat: Threat,
        description: str = "",
        enforcement_result: Optional[EnforcementResult] = None,
    ) -> Incident:
        """Create and process an incident from a detected threat."""
        severity = self._threat_severity_to_incident(threat.severity)
        incident_type = self._threat_category_to_type(threat.category)

        return self.create_incident(
            incident_type=incident_type,
            severity=severity,
            title=f"Threat detected: {threat.name}",
            description=description or threat.description,
            threats=[threat],
            enforcement_result=enforcement_result,
        )

    def handle_enforcement_result(
        self, result: EnforcementResult, context: dict[str, Any] | None = None
    ) -> Optional[Incident]:
        """Create an incident from a blocked enforcement result."""
        if result.allowed:
            return None  # Nothing to report if it was allowed

        # Determine severity from the blocked threats
        if result.blocked_threats:
            max_severity = max(
                t.severity for t in result.blocked_threats
            )
            severity = self._threat_severity_to_incident(max_severity)
        else:
            severity = IncidentSeverity.MEDIUM

        context = context or {}
        return self.create_incident(
            incident_type=IncidentType.POLICY_VIOLATION,
            severity=severity,
            title="Policy violation — operation blocked",
            description=result.reason,
            threats=result.blocked_threats,
            enforcement_result=result,
            metadata={
                "operation": context.get("operation", ""),
                "matched_rules": result.metadata.get("matched_rules", []),
            },
        )

    def create_incident(
        self,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        title: str,
        description: str,
        threats: list[Threat] | None = None,
        risk_assessments: list[RiskAssessment] | None = None,
        enforcement_result: Optional[EnforcementResult] = None,
        metadata: dict[str, Any] | None = None,
    ) -> Incident:
        """Create a new incident and trigger escalation if needed."""
        with self._lock:
            self._counter += 1
            incident_id = hashlib.sha256(
                f"incident_{self._counter}_{time.time()}".encode()
            ).hexdigest()[:12]

            incident = Incident(
                id=incident_id,
                incident_type=incident_type,
                severity=severity,
                title=title,
                description=description,
                threats=threats or [],
                risk_assessments=risk_assessments or [],
                enforcement_result=enforcement_result,
                metadata=metadata or {},
            )

            # Check suppression rules
            for rule in self._suppression_rules:
                if rule(incident):
                    return incident  # Created but not escalated

            self._incidents[incident_id] = incident
            self._increment_stats(severity)

            # Trigger escalation
            self._escalate(incident)

            return incident

    def resolve_incident(
        self,
        incident_id: str,
        resolver: str = "system",
        notes: str = "",
    ) -> bool:
        """Mark an incident as resolved."""
        with self._lock:
            incident = self._incidents.get(incident_id)
            if incident is None or incident.resolved:
                return False
            incident.resolved = True
            incident.resolved_at = time.time()
            incident.resolver = resolver
            incident.resolution_notes = notes
            self._stats["resolved_incidents"] += 1
            return True

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self._incidents.get(incident_id)

    def list_incidents(
        self,
        severity: Optional[IncidentSeverity] = None,
        resolved: Optional[bool] = None,
    ) -> list[Incident]:
        """List incidents, optionally filtered."""
        results = list(self._incidents.values())
        if severity is not None:
            results = [i for i in results if i.severity == severity]
        if resolved is not None:
            results = [i for i in results if i.resolved == resolved]
        return results

    def get_active_incidents(self) -> list[Incident]:
        """List unresolved incidents."""
        return [i for i in self._incidents.values() if not i.resolved]

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    def _escalate(self, incident: Incident) -> None:
        """Run escalation actions for an incident based on its severity."""
        actions = _SEVERITY_ESCALATION.get(incident.severity, [])
        incident.escalation_actions = list(actions)

        for action in actions:
            incident.escalation_level += 1
            self._stats["total_escalations"] += 1
            self._trigger_action(incident, action)

    def _trigger_action(self, incident: Incident, action: EscalationAction) -> Any:
        """Execute an escalation action via the handler and callbacks."""
        result = self._escalation_handler.handle(incident, action)

        # Invoke any registered callbacks for this action type
        callbacks = self._escalation_callbacks.get(action, [])
        callback_results = []
        for cb in callbacks:
            try:
                cb_result = cb(incident)
                callback_results.append(cb_result)
            except Exception as exc:  # noqa: BLE001
                callback_results.append(f"callback_error: {exc}")

        return {"handler_result": result, "callback_results": callback_results}

    def set_escalation_handler(self, handler: EscalationHandler) -> None:
        """Replace the escalation handler."""
        self._escalation_handler = handler

    def register_callback(
        self,
        action: EscalationAction,
        callback: Callable[[Incident], Any],
    ) -> None:
        """Register a callback for a specific escalation action."""
        self._escalation_callbacks.setdefault(action, []).append(callback)

    # ------------------------------------------------------------------
    # Suppression
    # ------------------------------------------------------------------

    def add_suppression_rule(self, rule: Callable[[Incident], bool]) -> None:
        """Add a rule that suppresses incidents matching the predicate."""
        self._suppression_rules.append(rule)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def get_incident_summary(self) -> dict[str, Any]:
        """Get a summary of all incidents."""
        with self._lock:
            active = self.get_active_incidents()
            by_severity: dict[str, int] = {}
            by_type: dict[str, int] = {}
            for inc in self._incidents.values():
                by_severity[inc.severity.value] = (
                    by_severity.get(inc.severity.value, 0) + 1
                )
                by_type[inc.incident_type.value] = (
                    by_type.get(inc.incident_type.value, 0) + 1
                )

            return {
                "total_incidents": len(self._incidents),
                "active_incidents": len(active),
                "resolved_incidents": sum(
                    1 for i in self._incidents.values() if i.resolved
                ),
                "by_severity": by_severity,
                "by_type": by_type,
                "stats": dict(self._stats),
            }

    def generate_report(self) -> dict[str, Any]:
        """Generate a full incident report."""
        with self._lock:
            return {
                "summary": self.get_incident_summary(),
                "incidents": [i.to_dict() for i in self._incidents.values()],
                "generated_at": time.time(),
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _increment_stats(self, severity: IncidentSeverity) -> None:
        self._stats["total_incidents"] += 1
        key = f"{severity.value}_incidents"
        if key in self._stats:
            self._stats[key] += 1

    @staticmethod
    def _threat_severity_to_incident(severity: ThreatSeverity) -> IncidentSeverity:
        mapping = {
            ThreatSeverity.CRITICAL: IncidentSeverity.CRITICAL,
            ThreatSeverity.HIGH: IncidentSeverity.HIGH,
            ThreatSeverity.MEDIUM: IncidentSeverity.MEDIUM,
            ThreatSeverity.LOW: IncidentSeverity.LOW,
            ThreatSeverity.INFO: IncidentSeverity.INFO,
        }
        return mapping.get(severity, IncidentSeverity.LOW)

    @staticmethod
    def _threat_category_to_type(category: ThreatCategory) -> IncidentType:
        mapping = {
            ThreatCategory.PROMPT_INJECTION: IncidentType.THREAT_DETECTED,
            ThreatCategory.DATA_EXFILTRATION: IncidentType.DATA_BREACH,
            ThreatCategory.PRIVILEGE_ESCALATION: IncidentType.SYSTEM_COMPROMISE,
            ThreatCategory.DENIAL_OF_SERVICE: IncidentType.RESOURCE_ABUSE,
            ThreatCategory.MODEL_MANIPULATION: IncidentType.THREAT_DETECTED,
            ThreatCategory.CREDENTIAL_THEFT: IncidentType.DATA_BREACH,
            ThreatCategory.UNAUTHORIZED_ACCESS: IncidentType.SUSPICIOUS_ACTIVITY,
            ThreatCategory.SIDE_CHANNEL: IncidentType.SUSPICIOUS_ACTIVITY,
        }
        # UNAUTHORIZED_ACCESS maps to SUSPICIOUS_ACTIVITY above.
        return mapping.get(category, IncidentType.CUSTOM)

    def reset(self) -> None:
        """Reset all incident state."""
        with self._lock:
            self._incidents.clear()
            self._counter = 0
            self._stats = {
                "total_incidents": 0,
                "critical_incidents": 0,
                "high_incidents": 0,
                "resolved_incidents": 0,
                "total_escalations": 0,
            }


__all__ = [
    "IncidentType",
    "IncidentSeverity",
    "EscalationAction",
    "Incident",
    "EscalationHandler",
    "LoggingEscalationHandler",
    "IncidentResponder",
]
=======
    """A safety incident opened by the responder."""

    incident_id: str
    level: IncidentLevel
    status: IncidentStatus
    title: str
    description: str
    enforcement_result: EnforcementResult | None = None
    detected_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    escalation_level: EscalationLevel | None = None
    assigned_to: str | None = None
    timeline: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "level": self.level.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "escalation_level": self.escalation_level.value if self.escalation_level else None,
            "assigned_to": self.assigned_to,
            "timeline": list(self.timeline),
            "metadata": dict(self.metadata),
            "detected_at": self.detected_at,
            "updated_at": self.updated_at,
        }

    def add_event(self, status: IncidentStatus, note: str = "") -> None:
        self.timeline.append({
            "status": status.value,
            "note": note,
            "timestamp": time.time(),
        })
        self.status = status
        self.updated_at = time.time()


class IncidentResponder:
    """Open, track, and escalate safety incidents."""

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}
        self._escalation_rules: dict[IncidentLevel, list[EscalationRule]] = {}
        self._notifications: list[dict[str, Any]] = []
        self._counter = 0

    # -- escalation rules ---------------------------------------------------

    def add_escalation_rule(self, level: IncidentLevel, rule: EscalationRule) -> None:
        self._escalation_rules.setdefault(level, []).append(rule)

    def clear_escalation_rules(self) -> None:
        self._escalation_rules.clear()

    def default_escalation_rules(self) -> None:
        """Seed sensible default escalation rules."""
        self.clear_escalation_rules()
        self.add_escalation_rule(
            IncidentLevel.LOW,
            EscalationRule(EscalationLevel.L1_OPERATIONAL, timeout_seconds=600,
                           description="Route to operational team lead")
        )
        self.add_escalation_rule(
            IncidentLevel.MEDIUM,
            EscalationRule(EscalationLevel.L1_OPERATIONAL, timeout_seconds=300,
                           description="Route to operational team lead")
        )
        self.add_escalation_rule(
            IncidentLevel.MEDIUM,
            EscalationRule(EscalationLevel.L2_SECURITY, timeout_seconds=300,
                           description="Escalate to security on-call if unresolved")
        )
        self.add_escalation_rule(
            IncidentLevel.HIGH,
            EscalationRule(EscalationLevel.L2_SECURITY, timeout_seconds=120,
                           description="Route directly to security on-call")
        )
        self.add_escalation_rule(
            IncidentLevel.HIGH,
            EscalationRule(EscalationLevel.L3_MANAGEMENT, timeout_seconds=120,
                           description="Escalate to management if unresolved")
        )
        self.add_escalation_rule(
            IncidentLevel.CRITICAL,
            EscalationRule(EscalationLevel.L3_MANAGEMENT, timeout_seconds=30,
                           description="Immediate management escalation")
        )
        self.add_escalation_rule(
            IncidentLevel.CRITICAL,
            EscalationRule(EscalationLevel.L4_EXTERNAL, timeout_seconds=30,
                           description="External / regulatory escalation")
        )

    # -- incident lifecycle -------------------------------------------------

    @staticmethod
    def _next_id(seed: str) -> str:
        digest = hashlib.sha256(f"{seed}-{time.time_ns()}".encode()).hexdigest()
        return digest[:16]

    def _level_from_result(self, result: EnforcementResult) -> IncidentLevel:
        level_map = {
            PolicyAction.BLOCK: IncidentLevel.CRITICAL,
            PolicyAction.ESCALATE: IncidentLevel.HIGH,
        }
        if result.action == PolicyAction.BLOCK:
            return IncidentLevel.CRITICAL
        if result.action == PolicyAction.ESCALATE:
            return IncidentLevel.HIGH
        # Blocked rules with critical severity => high.
        return IncidentLevel.MEDIUM

    def open_incident(
        self,
        title: str,
        description: str,
        level: IncidentLevel | None = None,
        enforcement_result: EnforcementResult | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Incident:
        """Open a new incident. If *level* is omitted it is inferred from the
        enforcement result (or defaults to MEDIUM)."""
        if level is None:
            if enforcement_result is not None:
                level = self._level_from_result(enforcement_result)
            else:
                level = IncidentLevel.MEDIUM

        incident_id = self._next_id(title)
        incident = Incident(
            incident_id=incident_id,
            level=level,
            status=IncidentStatus.DETECTED,
            title=title,
            description=description,
            enforcement_result=enforcement_result,
            timeline=[],
            metadata=metadata or {},
        )
        incident.add_event(IncidentStatus.DETECTED, "Incident detected")
        self._incidents[incident_id] = incident
        logger.warning("Opened incident %s (%s)", incident_id, level.value)
        self._notify(incident)
        return incident

    def handle_enforcement_result(
        self, result: EnforcementResult, context: dict[str, Any] | None = None
    ) -> Incident | None:
        """Open an incident if an enforcement result blocked or escalated."""
        if result.action in (PolicyAction.BLOCK, PolicyAction.ESCALATE):
            title = f"Safety policy {result.action.value} — level={result.risk_level.value}"
            description = result.reason or "Policy violation detected"
            return self.open_incident(
                title=title,
                description=description,
                enforcement_result=result,
                metadata={"violations": result.violations, **(context or {})},
            )
        return None

    def acknowledge(self, incident_id: str, by: str = "operator") -> Incident | None:
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        incident.add_event(IncidentStatus.ACKNOWLEDGED, f"Acknowledged by {by}")
        return incident

    def investigate(self, incident_id: str, note: str = "") -> Incident | None:
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        incident.add_event(IncidentStatus.INVESTIGATING, note)
        return incident

    def escalate(self, incident_id: str, to_level: EscalationLevel | None = None,
                 note: str = "") -> Incident | None:
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        rules = self._escalation_rules.get(incident.level, [])
        if not rules:
            # If no rules registered for this level, still allow manual escalation.
            if to_level is None:
                to_level = EscalationLevel.L1_OPERATIONAL
            incident.escalation_level = to_level
            incident.assigned_to = to_level.value
            incident.add_event(IncidentStatus.ESCALATED, note or f"Escalated to {to_level.value}")
            return incident

        if to_level is None:
            # Pick the next escalation level not yet applied.
            for rule in rules:
                if incident.escalation_level is None or incident.escalation_level.value < rule.level.value:
                    to_level = rule.level
                    break
            if to_level is None:
                to_level = rules[-1].level

        incident.escalation_level = to_level
        incident.assigned_to = to_level.value
        incident.add_event(IncidentStatus.ESCALATED, note or f"Escalated to {to_level.value}")

        # Fire the handler if one is attached.
        for rule in rules:
            if rule.level == to_level and rule.handler is not None:
                try:
                    rule.handler(incident)
                except Exception as exc:
                    logger.error("Escalation handler failed: %s", exc)
                break

        self._notify(incident)
        return incident

    def contain(self, incident_id: str, note: str = "") -> Incident | None:
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        incident.add_event(IncidentStatus.CONTAINED, note)
        return incident

    def resolve(self, incident_id: str, note: str = "", resolved_by: str = "operator") -> Incident | None:
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        incident.add_event(IncidentStatus.RESOLVED, f"{note} (by {resolved_by})")
        incident.add_event(IncidentStatus.CLOSED, f"Closed by {resolved_by}")
        return incident

    # -- queries ------------------------------------------------------------

    def get(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def list(self) -> list[Incident]:
        return list(self._incidents.values())

    def by_level(self, level: IncidentLevel) -> list[Incident]:
        return [i for i in self._incidents.values() if i.level == level]

    def by_status(self, status: IncidentStatus) -> list[Incident]:
        return [i for i in self._incidents.values() if i.status == status]

    def active_incidents(self) -> list[Incident]:
        terminal = {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
        return [i for i in self._incidents.values() if i.status not in terminal]

    @property
    def notification_log(self) -> list[dict[str, Any]]:
        return list(self._notifications)

    # -- internals ----------------------------------------------------------

    def _notify(self, incident: Incident) -> None:
        self._notifications.append({
            "incident_id": incident.incident_id,
            "level": incident.level.value,
            "status": incident.status.value,
            "timestamp": time.time(),
            "message": f"Incident {incident.incident_id} ({incident.level.value}) -> {incident.status.value}",
        })
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109
