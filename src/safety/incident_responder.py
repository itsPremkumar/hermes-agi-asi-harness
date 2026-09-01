"""Incident Responder — Handle security incidents and recovery."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class IncidentSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Incident:
    incident_id: str
    title: str
    severity: IncidentSeverity
    description: str
    status: IncidentStatus = IncidentStatus.OPEN
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    resolution: str | None = None


@dataclass
class ResponseAction:
    action_id: str
    incident_id: str
    action: str
    timestamp: float = field(default_factory=time.time)


class IncidentResponder:
    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._actions: list[ResponseAction] = []

    def create_incident(self, title: str, severity: IncidentSeverity, description: str) -> str:
        incident_id = f"inc-{int(time.time() * 1000)}-{len(self._incidents)}"
        incident = Incident(
            incident_id=incident_id,
            title=title,
            severity=severity,
            description=description,
        )
        self._incidents[incident_id] = incident
        return incident_id

    def get_incident(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def update_status(self, incident_id: str, status: IncidentStatus) -> bool:
        incident = self._incidents.get(incident_id)
        if not incident:
            return False
        incident.status = status
        incident.updated_at = time.time()
        return True

    def resolve(self, incident_id: str, resolution: str) -> bool:
        incident = self._incidents.get(incident_id)
        if not incident:
            return False
        incident.status = IncidentStatus.RESOLVED
        incident.resolution = resolution
        incident.updated_at = time.time()
        return True

    def add_action(self, incident_id: str, action: str) -> None:
        self._actions.append(ResponseAction(
            action_id=f"act-{int(time.time() * 1000)}",
            incident_id=incident_id,
            action=action,
        ))

    def get_actions(self, incident_id: str) -> list[ResponseAction]:
        return [a for a in self._actions if a.incident_id == incident_id]

    def list_incidents(self, status: IncidentStatus | None = None) -> list[Incident]:
        incidents = list(self._incidents.values())
        if status:
            incidents = [i for i in incidents if i.status == status]
        return incidents
