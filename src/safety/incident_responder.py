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
    "IncidentLevel",
    "IncidentStatus",
    "Incident",
    "IncidentResponder",
    "EscalationLevel",
    "EscalationRule",
]


class IncidentLevel(Enum):
    """Severity of a safety incident."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
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
    handler: Callable[["Incident"], Any] | None = None
    timeout_seconds: float = 300.0
    description: str = ""


@dataclass
class Incident:
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
                except Exception as exc:  # noqa: BLE001
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
