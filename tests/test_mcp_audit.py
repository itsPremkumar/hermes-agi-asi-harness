"""Tests for MCPAudit — logging, tracing, compliance tracking."""
from __future__ import annotations

import pytest

from harness.mcp.audit import MCPAudit, AuditEvent, AuditLevel


class TestAuditLevel:
    def test_values(self):
        assert AuditLevel.DEBUG.value == "debug"
        assert AuditLevel.INFO.value == "info"
        assert AuditLevel.WARNING.value == "warning"
        assert AuditLevel.ERROR.value == "error"
        assert AuditLevel.CRITICAL.value == "critical"


class TestAuditEvent:
    def test_create(self):
        event = AuditEvent(
            event_id="e1",
            timestamp=1234567890.0,
            level=AuditLevel.INFO,
            category="tool_call",
            message="test event",
        )
        assert event.event_id == "e1"
        assert event.level == AuditLevel.INFO
        assert event.category == "tool_call"
        assert event.message == "test event"
        assert event.success is True

    def test_to_dict(self):
        event = AuditEvent(
            event_id="e1",
            timestamp=1234567890.0,
            level=AuditLevel.INFO,
            category="tool_call",
            message="test",
            server_name="s1",
            tool_name="search",
        )
        d = event.to_dict()
        assert d["event_id"] == "e1"
        assert d["level"] == "info"
        assert d["category"] == "tool_call"
        assert d["server_name"] == "s1"
        assert d["tool_name"] == "search"


class TestMCPAudit:
    def test_create(self):
        audit = MCPAudit()
        assert audit.audit_id.startswith("audit-")
        assert audit.total_events == 0

    def test_log(self):
        audit = MCPAudit()
        event = audit.log(
            level=AuditLevel.INFO,
            category="tool_call",
            message="test event",
        )
        assert event.level == AuditLevel.INFO
        assert event.category == "tool_call"
        assert audit.total_events == 1

    def test_log_tool_call(self):
        audit = MCPAudit()
        event = audit.log_tool_call(
            server_name="s1",
            tool_name="search",
            success=True,
            duration_ms=150.0,
        )
        assert event.category == "tool_call"
        assert event.success is True
        assert event.duration_ms == 150.0

    def test_log_tool_call_failure(self):
        audit = MCPAudit()
        event = audit.log_tool_call(
            server_name="s1",
            tool_name="search",
            success=False,
            duration_ms=50.0,
            error="timeout",
        )
        assert event.level == AuditLevel.ERROR
        assert event.success is False

    def test_log_auth(self):
        audit = MCPAudit()
        event = audit.log_auth(
            server_name="s1",
            auth_method="api_key",
            success=True,
        )
        assert event.category == "auth"
        assert event.success is True

    def test_log_auth_failure(self):
        audit = MCPAudit()
        event = audit.log_auth(
            server_name="s1",
            auth_method="bearer_token",
            success=False,
            error="expired",
        )
        assert event.level == AuditLevel.ERROR

    def test_log_health(self):
        audit = MCPAudit()
        event = audit.log_health(
            server_name="s1",
            old_status="ready",
            new_status="degraded",
        )
        assert event.category == "health"
        assert event.level == AuditLevel.WARNING

    def test_log_health_unreachable(self):
        audit = MCPAudit()
        event = audit.log_health(
            server_name="s1",
            old_status="ready",
            new_status="unreachable",
        )
        assert event.level == AuditLevel.ERROR

    def test_log_connection(self):
        audit = MCPAudit()
        event = audit.log_connection(
            server_name="s1",
            connected=True,
        )
        assert event.category == "connection"
        assert event.success is True

    def test_log_connection_failure(self):
        audit = MCPAudit()
        event = audit.log_connection(
            server_name="s1",
            connected=False,
            error="refused",
        )
        assert event.level == AuditLevel.ERROR

    def test_log_config_change(self):
        audit = MCPAudit()
        event = audit.log_config_change(
            server_name="s1",
            change_type="update_tools",
        )
        assert event.category == "config"

    def test_get_events(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "event1")
        audit.log(AuditLevel.ERROR, "auth", "event2")
        events = audit.get_events()
        assert len(events) == 2

    def test_get_events_with_filter(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "event1")
        audit.log(AuditLevel.ERROR, "auth", "event2")
        events = audit.get_events(level=AuditLevel.ERROR)
        assert len(events) == 1
        assert events[0].level == AuditLevel.ERROR

    def test_get_events_with_category_filter(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "event1")
        audit.log(AuditLevel.INFO, "auth", "event2")
        events = audit.get_events(category="tool_call")
        assert len(events) == 1

    def test_get_events_with_server_filter(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "e1", server_name="s1")
        audit.log(AuditLevel.INFO, "tool_call", "e2", server_name="s2")
        events = audit.get_events(server_name="s1")
        assert len(events) == 1

    def test_get_events_with_tool_filter(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "e1", tool_name="search")
        audit.log(AuditLevel.INFO, "tool_call", "e2", tool_name="fetch")
        events = audit.get_events(tool_name="search")
        assert len(events) == 1

    def test_get_events_with_success_filter(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "e1", success=True)
        audit.log(AuditLevel.ERROR, "tool_call", "e2", success=False)
        events = audit.get_events(success=False)
        assert len(events) == 1

    def test_get_errors(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "ok")
        audit.log(AuditLevel.ERROR, "tool_call", "fail1")
        audit.log(AuditLevel.ERROR, "auth", "fail2")
        errors = audit.get_errors()
        assert len(errors) == 2

    def test_get_category_summary(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "e1")
        audit.log(AuditLevel.INFO, "tool_call", "e2")
        audit.log(AuditLevel.INFO, "auth", "e3")
        summary = audit.get_category_summary()
        assert summary["tool_call"] == 2
        assert summary["auth"] == 1

    def test_get_server_summary(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "e1", server_name="s1")
        audit.log(AuditLevel.INFO, "tool_call", "e2", server_name="s1")
        audit.log(AuditLevel.INFO, "tool_call", "e3", server_name="s2")
        summary = audit.get_server_summary()
        assert summary["s1"] == 2
        assert summary["s2"] == 1

    def test_get_recent_events(self):
        audit = MCPAudit()
        for i in range(10):
            audit.log(AuditLevel.INFO, "tool_call", f"event{i}")
        recent = audit.get_recent_events(count=5)
        assert len(recent) == 5

    def test_on_event(self):
        audit = MCPAudit()
        events_received = []
        audit.on_event(lambda evt: events_received.append(evt))
        audit.log(AuditLevel.INFO, "tool_call", "test")
        assert len(events_received) == 1

    def test_export_json(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "test")
        json_str = audit.export_json()
        assert "tool_call" in json_str

    def test_clear(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "test")
        audit.clear()
        assert audit.total_events == 0

    def test_get_stats(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "ok")
        audit.log(AuditLevel.ERROR, "tool_call", "fail")
        stats = audit.get_stats()
        assert stats["total_events"] == 2
        assert stats["error_count"] == 1
        assert stats["servers_tracked"] == 0

    def test_get_timeline(self):
        audit = MCPAudit()
        audit.log(AuditLevel.INFO, "tool_call", "e1", server_name="s1")
        audit.log(AuditLevel.INFO, "tool_call", "e2", server_name="s1")
        timeline = audit.get_timeline(server_name="s1", bucket_seconds=60, num_buckets=10)
        assert len(timeline) >= 1
        assert timeline[0]["count"] >= 2

    def test_max_events_trim(self):
        audit = MCPAudit(max_events=5)
        for i in range(10):
            audit.log(AuditLevel.INFO, "tool_call", f"event{i}")
        assert audit.total_events == 5
