"""Tests for MCPBridge — maps MCP tools to harness tool calls."""
from __future__ import annotations

import pytest

from harness.mcp.bridge import MCPBridge, ToolMapping
from harness.mcp.registry import MCPRegistry, ServerStatus


class TestToolMapping:
    def test_create(self):
        mapping = ToolMapping(
            harness_tool_name="search",
            mcp_tool_name="web_search",
            server_id="srv-1",
            server_name="search-server",
        )
        assert mapping.harness_tool_name == "search"
        assert mapping.mcp_tool_name == "web_search"
        assert mapping.server_id == "srv-1"

    def test_qualified_name(self):
        mapping = ToolMapping(
            harness_tool_name="search",
            mcp_tool_name="web_search",
            server_id="srv-1",
            server_name="search-server",
        )
        assert mapping.qualified_name == "mcp__search-server__web_search"

    def test_qualified_name_with_underscores(self):
        mapping = ToolMapping(
            harness_tool_name="my_tool",
            mcp_tool_name="my_tool_v2",
            server_id="srv-1",
            server_name="my_server",
        )
        assert mapping.qualified_name == "mcp__my_server__my_tool_v2"


class TestMCPBridge:
    def test_create(self):
        registry = MCPRegistry()
        bridge = MCPBridge(registry)
        assert bridge.bridge_id.startswith("bridge-")
        assert bridge.tool_count == 0

    def test_register_tool(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        mapping = bridge.register_tool(
            harness_tool_name="search",
            mcp_tool_name="web_search",
            server_id=info.server_id,
            description="Search the web",
        )
        assert mapping.harness_tool_name == "search"
        assert bridge.tool_count == 1

    def test_register_tool_server_not_found(self):
        registry = MCPRegistry()
        bridge = MCPBridge(registry)
        with pytest.raises(ValueError, match="not found"):
            bridge.register_tool(
                harness_tool_name="search",
                mcp_tool_name="web_search",
                server_id="nonexistent",
            )

    def test_unregister_tool(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool(
            harness_tool_name="search",
            mcp_tool_name="web_search",
            server_id=info.server_id,
        )
        assert bridge.unregister_tool("search") is True
        assert bridge.tool_count == 0

    def test_unregister_nonexistent(self):
        registry = MCPRegistry()
        bridge = MCPBridge(registry)
        assert bridge.unregister_tool("nonexistent") is False

    def test_get_mapping(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool(
            harness_tool_name="search",
            mcp_tool_name="web_search",
            server_id=info.server_id,
        )
        mapping = bridge.get_mapping("search")
        assert mapping is not None
        assert mapping.mcp_tool_name == "web_search"

    def test_get_mapping_by_qualified(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool(
            harness_tool_name="search",
            mcp_tool_name="web_search",
            server_id=info.server_id,
        )
        mapping = bridge.get_mapping_by_qualified("mcp__s1__web_search")
        assert mapping is not None
        assert mapping.harness_tool_name == "search"

    def test_list_tools(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool("search", "web_search", info.server_id)
        bridge.register_tool("fetch", "web_fetch", info.server_id)
        tools = bridge.list_tools()
        assert len(tools) == 2

    def test_list_available_tools(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        registry.update_status(info.server_id, ServerStatus.READY)
        bridge = MCPBridge(registry)
        bridge.register_tool("search", "web_search", info.server_id)
        bridge.register_tool("fetch", "web_fetch", info.server_id)
        available = bridge.list_available_tools()
        assert len(available) == 2

    def test_list_available_tools_only_ready(self):
        registry = MCPRegistry()
        info1 = registry.register(name="s1", transport="stdio", endpoint="cmd1")
        info2 = registry.register(name="s2", transport="stdio", endpoint="cmd2")
        registry.update_status(info1.server_id, ServerStatus.READY)
        # s2 remains UNKNOWN
        bridge = MCPBridge(registry)
        bridge.register_tool("search", "web_search", info1.server_id)
        bridge.register_tool("fetch", "web_fetch", info2.server_id)
        available = bridge.list_available_tools()
        assert len(available) == 1

    def test_call_tool_not_registered(self):
        registry = MCPRegistry()
        bridge = MCPBridge(registry)
        with pytest.raises(ValueError, match="not registered"):
            bridge.call_tool("nonexistent")

    def test_get_stats(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool("search", "web_search", info.server_id)
        stats = bridge.get_stats()
        assert stats["registered_tools"] == 1
        assert stats["total_clients"] == 0

    def test_get_tool_manifest(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool(
            harness_tool_name="search",
            mcp_tool_name="web_search",
            server_id=info.server_id,
            description="Search the web",
        )
        manifest = bridge.get_tool_manifest()
        assert len(manifest) == 1
        assert manifest[0]["harness_name"] == "search"
        assert manifest[0]["mcp_name"] == "web_search"
        assert manifest[0]["description"] == "Search the web"

    def test_clear(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool("search", "web_search", info.server_id)
        bridge.clear()
        assert bridge.tool_count == 0

    def test_on_pre_call(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool("search", "web_search", info.server_id)
        calls = []
        bridge.on_pre_call(lambda name, args: calls.append((name, args)))
        # Pre-call hook is invoked during call_tool
        # (actual invocation requires a connected client)
        assert len(calls) == 0  # No call made yet

    def test_on_post_call(self):
        registry = MCPRegistry()
        info = registry.register(name="s1", transport="stdio", endpoint="cmd")
        bridge = MCPBridge(registry)
        bridge.register_tool("search", "web_search", info.server_id)
        calls = []
        bridge.on_post_call(lambda name, result, elapsed: calls.append(name))
        assert len(calls) == 0

    def test_discover_and_register_server_not_found(self):
        registry = MCPRegistry()
        bridge = MCPBridge(registry)
        with pytest.raises(ValueError, match="not found"):
            bridge.discover_and_register("nonexistent")
