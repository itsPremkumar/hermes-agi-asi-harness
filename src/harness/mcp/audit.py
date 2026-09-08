"""MCPAudit — logging, tracing, compliance tracking.

Provides comprehensive audit logging for MCP operations including
tool calls, authentication events, and server health changes.
Supports structured logging, filtering, and export.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


class AuditLevel(Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """A single audit event."""
    event_id: str
    timestamp: float
    level: AuditLevel
    category: str  # "tool_call", "auth", "health", "connection", "config"
    message: str
    server_id: Optional[str] = None
    server_name: Optional[str] = None
    tool_name: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "category": self.category,
            "message": self.message,
            "server_id": self.server_id,
            "server_name": self.server_name,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "details": self.details,
        }


class MCPAudit:
    """Audit logger for MCP operations.

    Records all MCP-related events for compliance, debugging,
    and operational monitoring. Thread-safe.
    """

    def __init__(self, max_events: int = 10000):
        self._events: List[AuditEvent] = []
        self._max_events = max_events
        self._lock = threading.RLock()
        self._audit_id = f"audit-{uuid.uuid4().hex[:12]}"
        self._error_count = 0
        self._warning_count = 0
        self._event_callbacks: List[Callable[[AuditEvent], None]] = []
        self._category_counts: Dict[str, int] = defaultdict(int)
        self._server_event_counts: Dict[str, int] = defaultdict(int)

    @property
    def audit_id(self) -> str:
        return self._audit_id

    @property
    def total_events(self) -> int:
        return len(self._events)

    # -- Event Logging ------------------------------------------------------

    def log(
        self,
        level: AuditLevel,
        category: str,
        message: str,
        server_id: Optional[str] = None,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            event_id=f"evt-{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            level=level,
            category=category,
            message=message,
            server_id=server_id,
            server_name=server_name,
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=success,
            details=dict(details or {}),
        )

        with self._lock:
            self._events.append(event)
            self._category_counts[category] += 1
            if server_name:
                self._server_event_counts[server_name] += 1

            # Update counters
            if level == AuditLevel.ERROR or level == AuditLevel.CRITICAL:
                self._error_count += 1
            elif level == AuditLevel.WARNING:
                self._warning_count += 1

            # Trim if over max
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events :]

        # Fire callbacks
        for cb in self._event_callbacks:
            try:
                cb(event)
            except Exception:
                pass

        return event

    def log_tool_call(
        self,
        server_name: str,
        tool_name: str,
        success: bool,
        duration_ms: float,
        server_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> AuditEvent:
        """Log a tool call event."""
        level = AuditLevel.INFO if success else AuditLevel.ERROR
        message = f"Tool '{tool_name}' on '{server_name}' "
        message += "succeeded" if success else f"failed: {error}"

        return self.log(
            level=level,
            category="tool_call",
            message=message,
            server_id=server_id,
            server_name=server_name,
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=success,
            details={"error": error} if error else None,
        )

    def log_auth(
        self,
        server_name: str,
        auth_method: str,
        success: bool,
        error: Optional[str] = None,
    ) -> AuditEvent:
        """Log an authentication event."""
        level = AuditLevel.INFO if success else AuditLevel.ERROR
        message = f"Auth ({auth_method}) for '{server_name}' "
        message += "succeeded" if success else f"failed: {error}"

        return self.log(
            level=level,
            category="auth",
            message=message,
            server_name=server_name,
            success=success,
            details={"auth_method": auth_method, "error": error},
        )

    def log_health(
        self,
        server_name: str,
        old_status: str,
        new_status: str,
        server_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log a health status change."""
        level = AuditLevel.INFO
        if new_status in ("unreachable", "error"):
            level = AuditLevel.ERROR
        elif new_status == "degraded":
            level = AuditLevel.WARNING

        return self.log(
            level=level,
            category="health",
            message=f"Health change for '{server_name}': {old_status} -> {new_status}",
            server_id=server_id,
            server_name=server_name,
            details={"old_status": old_status, "new_status": new_status},
        )

    def log_connection(
        self,
        server_name: str,
        connected: bool,
        error: Optional[str] = None,
    ) -> AuditEvent:
        """Log a connection event."""
        level = AuditLevel.INFO if connected else AuditLevel.ERROR
        message = f"Connection to '{server_name}' "
        message += "established" if connected else f"failed: {error}"

        return self.log(
            level=level,
            category="connection",
            message=message,
            server_name=server_name,
            success=connected,
            details={"error": error} if error else None,
        )

    def log_config_change(
        self,
        server_name: str,
        change_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log a configuration change."""
        return self.log(
            level=AuditLevel.INFO,
            category="config",
            message=f"Config change ({change_type}) for '{server_name}'",
            server_name=server_name,
            details=details,
        )

    # -- Filtering & Query --------------------------------------------------

    def get_events(
        self,
        level: Optional[AuditLevel] = None,
        category: Optional[str] = None,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query events with filters."""
        results = self._events

        if level:
            results = [e for e in results if e.level == level]
        if category:
            results = [e for e in results if e.category == category]
        if server_name:
            results = [e for e in results if e.server_name == server_name]
        if tool_name:
            results = [e for e in results if e.tool_name == tool_name]
        if success is not None:
            results = [e for e in results if e.success == success]

        return results[-limit:]

    def get_errors(self, limit: int = 100) -> List[AuditEvent]:
        """Get recent error events."""
        return self.get_events(level=AuditLevel.ERROR, limit=limit)

    def get_category_summary(self) -> Dict[str, int]:
        """Get event counts by category."""
        return dict(self._category_counts)

    def get_server_summary(self) -> Dict[str, int]:
        """Get event counts by server."""
        return dict(self._server_event_counts)

    def get_recent_events(self, count: int = 50) -> List[AuditEvent]:
        """Get the most recent events."""
        return self._events[-count:]

    # -- Hooks --------------------------------------------------------------

    def on_event(self, callback: Callable[[AuditEvent], None]) -> None:
        """Register an event callback."""
        self._event_callbacks.append(callback)

    # -- Export -------------------------------------------------------------

    def export_json(self, events: Optional[List[AuditEvent]] = None) -> str:
        """Export events as JSON."""
        events = events or self._events
        return json.dumps([e.to_dict() for e in events], indent=2, default=str)

    def clear(self) -> None:
        """Clear all events."""
        with self._lock:
            self._events.clear()
            self._category_counts.clear()
            self._server_event_counts.clear()
            self._error_count = 0
            self._warning_count = 0

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        return {
            "audit_id": self._audit_id,
            "total_events": len(self._events),
            "error_count": self._error_count,
            "warning_count": self._warning_count,
            "max_events": self._max_events,
            "category_breakdown": dict(self._category_counts),
            "servers_tracked": len(self._server_event_counts),
        }

    def get_timeline(
        self,
        server_name: Optional[str] = None,
        bucket_seconds: float = 60.0,
        num_buckets: int = 60,
    ) -> List[Dict[str, Any]]:
        """Get a timeline of event counts in time buckets."""
        now = time.time()
        buckets: Dict[int, Dict[str, Any]] = {}

        for event in self._events:
            if server_name and event.server_name != server_name:
                continue

            bucket_idx = int((now - event.timestamp) / bucket_seconds)
            if bucket_idx >= num_buckets:
                continue

            if bucket_idx not in buckets:
                bucket_start = now - (bucket_idx + 1) * bucket_seconds
                buckets[bucket_idx] = {
                    "start_time": bucket_start,
                    "end_time": bucket_start + bucket_seconds,
                    "count": 0,
                    "errors": 0,
                    "warnings": 0,
                }

            buckets[bucket_idx]["count"] += 1
            if event.level == AuditLevel.ERROR or event.level == AuditLevel.CRITICAL:
                buckets[bucket_idx]["errors"] += 1
            elif event.level == AuditLevel.WARNING:
                buckets[bucket_idx]["warnings"] += 1

        return [buckets[i] for i in sorted(buckets.keys())]
