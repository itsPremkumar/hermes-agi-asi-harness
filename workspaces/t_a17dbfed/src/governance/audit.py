"""Audit trail module — Logging and tracking for governance actions."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditTrail:
    """An audit trail entry."""
    id: str
    action: str
    actor: str
    resource: str
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """Log audit trail entries."""

    def __init__(self) -> None:
        self._entries: list[AuditTrail] = []

    def log(self, action: str, actor: str, resource: str, details: dict[str, Any] | None = None) -> AuditTrail:
        entry = AuditTrail(
            id=str(uuid.uuid4()),
            action=action,
            actor=actor,
            resource=resource,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details or {},
        )
        self._entries.append(entry)
        return entry

    def get_all(self) -> list[AuditTrail]:
        return list(self._entries)

    def get_by_actor(self, actor: str) -> list[AuditTrail]:
        return [e for e in self._entries if e.actor == actor]

    def get_by_resource(self, resource: str) -> list[AuditTrail]:
        return [e for e in self._entries if e.resource == resource]

    def get_by_action(self, action: str) -> list[AuditTrail]:
        return [e for e in self._entries if e.action == action]
