"""Tests for MCPClient — connection management, tool invocation, error handling."""
from __future__ import annotations

import pytest

from harness.mcp.client import (
    MCPClient,
    ConnectionConfig,
    ConnectionState,
    MCPConnectionError,
    MCPTimeoutError,
    MCPToolError,
)


class TestConnectionConfig:
    def test_defaults(self):
        config = ConnectionConfig()
        assert config.transport == "stdio"
        assert config.command == ""
        assert config.connect_timeout == 10.0
        assert config.call_timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_backoff == 0.5

    def test_stdio_config(self):
        config = ConnectionConfig(
            transport="stdio",
            command="python",
            args=["-m", "test_server"],
            env={"KEY": "value"},
        )
        assert config.transport == "stdio"
        assert config.command == "python"
        assert config.args == ["-m", "test_server"]
        assert config.env == {"KEY": "value"}

    def test_http_config(self):
        config = ConnectionConfig(
            transport="http",
            url="http://localhost:8080",
            headers={"Authorization": "Bearer token"},
        )
        assert config.transport == "http"
        assert config.url == "http://localhost:8080"
        assert config.headers == {"Authorization": "Bearer token"}


class TestMCPClient:
    def test_create(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.name == "test"
        assert client.state == ConnectionState.DISCONNECTED
        assert client.is_connected is False
        assert client.client_id.startswith("client-")

    def test_create_with_http(self):
        config = ConnectionConfig(transport="http", url="http://localhost:8080")
        client = MCPClient(config=config, name="http-test")
        assert client.name == "http-test"
        assert client.state == ConnectionState.DISCONNECTED

    def test_tool_names_empty(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.tool_names == set()

    def test_has_tool_false_when_disconnected(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.has_tool("any_tool") is False

    def test_call_tool_not_connected(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        with pytest.raises(MCPConnectionError, match="not connected"):
            client.call_tool("some_tool")

    def test_list_tools_not_connected(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        with pytest.raises(MCPConnectionError, match="not connected"):
            client.list_tools()

    def test_get_tool_not_found(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.get_tool("nonexistent") is None

    def test_get_tool_schema_not_found(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.get_tool_schema("nonexistent") is None

    def test_health_check_disconnected(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.health_check() is False

    def test_get_metrics(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        metrics = client.get_metrics()
        assert metrics["name"] == "test"
        assert metrics["state"] == "disconnected"
        assert metrics["tools_count"] == 0
        assert metrics["call_count"] == 0
        assert metrics["error_count"] == 0

    def test_uptime_zero_when_disconnected(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.uptime == 0.0

    def test_idle_time(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.idle_time >= 0

    def test_disconnect_when_disconnected(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        # Should not raise
        client.disconnect()
        assert client.state == ConnectionState.DISCONNECTED

    def test_reconnect_when_disconnected(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        # Reconnect will fail because echo is not an MCP server
        # but it should handle the error gracefully
        with pytest.raises(MCPConnectionError):
            client.reconnect()

    def test_call_count_increment(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.call_count == 0
        # Simulate incrementing
        client._call_count += 1
        assert client.call_count == 1

    def test_error_count_increment(self):
        config = ConnectionConfig(transport="stdio", command="echo")
        client = MCPClient(config=config, name="test")
        assert client.error_count == 0
        client._error_count += 1
        assert client.error_count == 1


class TestConnectionState:
    def test_values(self):
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.RECONNECTING.value == "reconnecting"
        assert ConnectionState.FAILED.value == "failed"


class TestMCPToolError:
    def test_create(self):
        err = MCPToolError("test_tool", "something went wrong")
        assert err.tool_name == "test_tool"
        assert "test_tool" in str(err)
        assert "something went wrong" in str(err)


class TestMCPConnectionError:
    def test_create(self):
        err = MCPConnectionError("connection failed")
        assert "connection failed" in str(err)


class TestMCPTimeoutError:
    def test_create(self):
        err = MCPTimeoutError("timeout after 30s")
        assert "timeout after 30s" in str(err)


class TestMCPClientAdvanced:
    def test_sanitize_tool_name(self):
        from harness.mcp.bridge import MCPBridge
        assert MCPBridge.sanitize_tool_name("search_tool") == "search_tool"
        assert MCPBridge.sanitize_tool_name("search-tool") == "search_tool"
        assert MCPBridge.sanitize_tool_name("search.tool") == "search_tool"
        assert MCPBridge.sanitize_tool_name("123tool") == "tool"

    def test_convert_mcp_schema(self):
        from harness.mcp.bridge import MCPBridge
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
        converted = MCPBridge.convert_mcp_schema(schema)
        assert converted["type"] == "object"
        assert "query" in converted["properties"]
        assert "query" in converted["required"]

    def test_convert_mcp_schema_empty(self):
        from harness.mcp.bridge import MCPBridge
        converted = MCPBridge.convert_mcp_schema({})
        assert converted["type"] == "object"
        assert converted["properties"] == {}
        assert converted["required"] == []

    def test_validate_arguments_required(self):
        from harness.mcp.bridge import MCPBridge
        schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }
        # Should raise for missing required field
        with pytest.raises(ValueError, match="Missing required argument"):
            MCPBridge._validate_arguments({}, schema)

    def test_validate_arguments_type_check(self):
        from harness.mcp.bridge import MCPBridge
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": [],
        }
        # Should raise for wrong type
        with pytest.raises(TypeError, match="expected integer"):
            MCPBridge._validate_arguments({"count": "not_a_number"}, schema)

    def test_validate_arguments_valid(self):
        from harness.mcp.bridge import MCPBridge
        schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }
        # Should not raise
        MCPBridge._validate_arguments({"query": "test"}, schema)
