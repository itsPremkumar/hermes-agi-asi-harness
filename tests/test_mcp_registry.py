"""Tests for MCPRegistry — server registration, health tracking, capability discovery."""
from __future__ import annotations

import pytest

from harness.mcp.registry import MCPRegistry, MCPServerInfo, ServerStatus


class TestMCPServerInfo:
    def test_create(self):
        info = MCPServerInfo(
            server_id="srv-1",
            name="test-server",
            transport="stdio",
            endpoint="python -m test_server",
        )
        assert info.server_id == "srv-1"
        assert info.name == "test-server"
        assert info.transport == "stdio"
        assert info.status == ServerStatus.UNKNOWN
        assert info.is_available is False
        assert info.age_seconds >= 0

    def test_to_dict(self):
        info = MCPServerInfo(
            server_id="srv-1",
            name="test-server",
            transport="http",
            endpoint="http://localhost:8080",
            capabilities=["tools", "resources"],
            tools=["search", "fetch"],
        )
        d = info.to_dict()
        assert d["server_id"] == "srv-1"
        assert d["name"] == "test-server"
        assert d["transport"] == "http"
        assert d["capabilities"] == ["tools", "resources"]
        assert d["tools"] == ["search", "fetch"]
        assert d["status"] == "unknown"

    def test_is_available_ready(self):
        info = MCPServerInfo(
            server_id="srv-1",
            name="test",
            transport="stdio",
            endpoint="cmd",
            status=ServerStatus.READY,
        )
        assert info.is_available is True

    def test_is_available_degraded(self):
        info = MCPServerInfo(
            server_id="srv-1",
            name="test",
            transport="stdio",
            endpoint="cmd",
            status=ServerStatus.DEGRADED,
        )
        assert info.is_available is True

    def test_is_available_unreachable(self):
        info = MCPServerInfo(
            server_id="srv-1",
            name="test",
            transport="stdio",
            endpoint="cmd",
            status=ServerStatus.UNREACHABLE,
        )
        assert info.is_available is False


class TestMCPRegistry:
    def test_create(self):
        reg = MCPRegistry()
        assert reg.server_count == 0
        assert reg.registry_id.startswith("registry-")

    def test_register(self):
        reg = MCPRegistry()
        info = reg.register(
            name="test-server",
            transport="stdio",
            endpoint="python -m test_server",
        )
        assert info.name == "test-server"
        assert info.server_id.startswith("mcp-")
        assert reg.server_count == 1

    def test_register_with_capabilities_and_tools(self):
        reg = MCPRegistry()
        info = reg.register(
            name="test-server",
            transport="http",
            endpoint="http://localhost:8080",
            capabilities=["tools", "resources"],
            tools=["search", "fetch"],
            tags={"production", "search"},
        )
        assert info.capabilities == ["tools", "resources"]
        assert info.tools == ["search", "fetch"]
        assert info.tags == {"production", "search"}

    def test_register_duplicate_name_raises(self):
        reg = MCPRegistry()
        reg.register(name="test", transport="stdio", endpoint="cmd")
        with pytest.raises(ValueError, match="already registered"):
            reg.register(name="test", transport="stdio", endpoint="cmd")

    def test_register_duplicate_id_raises(self):
        reg = MCPRegistry()
        reg.register(name="test1", transport="stdio", endpoint="cmd", server_id="same-id")
        with pytest.raises(ValueError, match="already exists"):
            reg.register(name="test2", transport="stdio", endpoint="cmd", server_id="same-id")

    def test_deregister(self):
        reg = MCPRegistry()
        info = reg.register(name="test", transport="stdio", endpoint="cmd")
        assert reg.deregister(info.server_id) is True
        assert reg.server_count == 0

    def test_deregister_nonexistent(self):
        reg = MCPRegistry()
        assert reg.deregister("nonexistent") is False

    def test_get(self):
        reg = MCPRegistry()
        info = reg.register(name="test", transport="stdio", endpoint="cmd")
        result = reg.get(info.server_id)
        assert result is not None
        assert result.name == "test"

    def test_get_by_name(self):
        reg = MCPRegistry()
        reg.register(name="test", transport="stdio", endpoint="cmd")
        result = reg.get_by_name("test")
        assert result is not None
        assert result.name == "test"

    def test_get_by_name_nonexistent(self):
        reg = MCPRegistry()
        assert reg.get_by_name("nonexistent") is None

    def test_get_all(self):
        reg = MCPRegistry()
        reg.register(name="s1", transport="stdio", endpoint="cmd1")
        reg.register(name="s2", transport="http", endpoint="http://localhost")
        all_servers = reg.get_all()
        assert len(all_servers) == 2

    def test_get_available(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd")
        reg.update_status(info.server_id, ServerStatus.READY)
        reg.register(name="s2", transport="stdio", endpoint="cmd2")
        available = reg.get_available()
        assert len(available) == 1
        assert available[0].name == "s1"

    def test_get_by_status(self):
        reg = MCPRegistry()
        info1 = reg.register(name="s1", transport="stdio", endpoint="cmd1")
        info2 = reg.register(name="s2", transport="stdio", endpoint="cmd2")
        reg.update_status(info1.server_id, ServerStatus.READY)
        reg.update_status(info2.server_id, ServerStatus.UNREACHABLE)
        ready = reg.get_by_status(ServerStatus.READY)
        assert len(ready) == 1
        assert ready[0].name == "s1"

    def test_get_by_tag(self):
        reg = MCPRegistry()
        reg.register(name="s1", transport="stdio", endpoint="cmd1", tags={"prod", "search"})
        reg.register(name="s2", transport="stdio", endpoint="cmd2", tags={"dev"})
        prod_servers = reg.get_by_tag("prod")
        assert len(prod_servers) == 1
        assert prod_servers[0].name == "s1"

    def test_get_by_capability(self):
        reg = MCPRegistry()
        reg.register(name="s1", transport="stdio", endpoint="cmd1", capabilities=["tools"])
        reg.register(name="s2", transport="stdio", endpoint="cmd2", capabilities=["resources"])
        tool_servers = reg.get_by_capability("tools")
        assert len(tool_servers) == 1
        assert tool_servers[0].name == "s1"

    def test_find_servers_for_tool(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd1", tools=["search", "fetch"])
        servers = reg.find_servers_for_tool("search")
        assert len(servers) == 1
        assert servers[0].server_id == info.server_id

    def test_find_available_servers_for_tool(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd1", tools=["search"])
        reg.update_status(info.server_id, ServerStatus.READY)
        reg.register(name="s2", transport="stdio", endpoint="cmd2", tools=["search"])
        available = reg.find_available_servers_for_tool("search")
        assert len(available) == 1
        assert available[0].name == "s1"

    def test_list_all_tools(self):
        reg = MCPRegistry()
        reg.register(name="s1", transport="stdio", endpoint="cmd1", tools=["search", "fetch"])
        reg.register(name="s2", transport="stdio", endpoint="cmd2", tools=["search"])
        tools = reg.list_all_tools()
        assert "search" in tools
        assert "fetch" in tools
        assert len(tools["search"]) == 2

    def test_list_all_capabilities(self):
        reg = MCPRegistry()
        reg.register(name="s1", transport="stdio", endpoint="cmd1", capabilities=["tools", "resources"])
        caps = reg.list_all_capabilities()
        assert "tools" in caps
        assert "resources" in caps

    def test_update_status(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd")
        assert reg.update_status(info.server_id, ServerStatus.READY) is True
        assert reg.get(info.server_id).status == ServerStatus.READY

    def test_update_status_nonexistent(self):
        reg = MCPRegistry()
        assert reg.update_status("nonexistent", ServerStatus.READY) is False

    def test_record_health_check_success(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd")
        assert reg.record_health_check(info.server_id, success=True) is True
        assert reg.get(info.server_id).status == ServerStatus.READY
        assert reg.get(info.server_id).health_check_failures == 0

    def test_record_health_check_failure(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd")
        assert reg.record_health_check(info.server_id, success=False) is True
        assert reg.get(info.server_id).status == ServerStatus.UNREACHABLE
        assert reg.get(info.server_id).health_check_failures == 1

    def test_on_status_change(self):
        reg = MCPRegistry()
        changes = []
        reg.on_status_change(lambda sid, old, new: changes.append((sid, old, new)))
        info = reg.register(name="s1", transport="stdio", endpoint="cmd")
        reg.update_status(info.server_id, ServerStatus.READY)
        assert len(changes) == 1
        assert changes[0][2] == ServerStatus.READY

    def test_update_tools(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd", tools=["old_tool"])
        assert reg.update_tools(info.server_id, ["new_tool1", "new_tool2"]) is True
        assert reg.get(info.server_id).tools == ["new_tool1", "new_tool2"]
        assert len(reg.find_servers_for_tool("old_tool")) == 0
        assert len(reg.find_servers_for_tool("new_tool1")) == 1

    def test_update_capabilities(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd", capabilities=["tools"])
        assert reg.update_capabilities(info.server_id, ["resources", "prompts"]) is True
        assert reg.get(info.server_id).capabilities == ["resources", "prompts"]
        assert len(reg.get_by_capability("tools")) == 0
        assert len(reg.get_by_capability("resources")) == 1

    def test_get_stats(self):
        reg = MCPRegistry()
        info = reg.register(name="s1", transport="stdio", endpoint="cmd", tools=["t1"])
        reg.update_status(info.server_id, ServerStatus.READY)
        stats = reg.get_stats()
        assert stats["total_servers"] == 1
        assert stats["total_tools"] == 1
        assert "ready" in stats["status_breakdown"]

    def test_get_health_summary(self):
        reg = MCPRegistry()
        info1 = reg.register(name="s1", transport="stdio", endpoint="cmd1")
        info2 = reg.register(name="s2", transport="stdio", endpoint="cmd2")
        reg.update_status(info1.server_id, ServerStatus.READY)
        reg.update_status(info2.server_id, ServerStatus.UNREACHABLE)
        summary = reg.get_health_summary()
        assert "s1" in summary["healthy"]
        assert "s2" in summary["unreachable"]
        assert summary["total"] == 2
        assert summary["available_count"] == 1

    def test_clear(self):
        reg = MCPRegistry()
        reg.register(name="s1", transport="stdio", endpoint="cmd1")
        reg.register(name="s2", transport="stdio", endpoint="cmd2")
        reg.clear()
        assert reg.server_count == 0
        assert len(reg.get_all()) == 0
