"""Tests for MCP Integration Plugin — IPlugin entry point."""

from __future__ import annotations

import asyncio
import tempfile

import pytest

from core.mcp_integration.plugin import MCPIntegrationPlugin
from core.mcp_integration.server_registry import MCPServerRecord, MCPServerRegistry
from harness_control_plane import TaskRequest, TaskResult


class TestMCPIntegrationPlugin:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.config_path = str(tmp_path / "mcp_servers.json")
        self.plugin = MCPIntegrationPlugin()

    @pytest.mark.asyncio
    async def test_create(self):
        assert self.plugin.name == "mcp-integration"
        assert self.plugin.version == "1.0.0"
        assert "mcp_server_registry" in self.plugin.capabilities
        assert "mcp_tool_bridge" in self.plugin.capabilities
        assert "mcp_health_monitoring" in self.plugin.capabilities

    @pytest.mark.asyncio
    async def test_initialize(self):
        await self.plugin.initialize({"config_path": self.config_path})
        assert self.plugin.is_initialized
        assert self.plugin.registry is not None
        assert self.plugin.bridge is not None

    @pytest.mark.asyncio
    async def test_health_check_before_init(self):
        assert await self.plugin.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_after_init(self):
        await self.plugin.initialize({"config_path": self.config_path})
        assert await self.plugin.health_check() is True

    @pytest.mark.asyncio
    async def test_execute_before_init(self):
        task = TaskRequest(task_id="t", task_type="list_servers", payload={})
        result = await self.plugin.execute(task)
        assert not result.success
        assert "not initialized" in result.error

    @pytest.mark.asyncio
    async def test_list_servers_empty(self):
        await self.plugin.initialize({"config_path": self.config_path})
        task = TaskRequest(task_id="t", task_type="list_servers", payload={})
        result = await self.plugin.execute(task)
        assert result.success
        assert result.result == []

    @pytest.mark.asyncio
    async def test_register_and_list(self):
        await self.plugin.initialize({"config_path": self.config_path})

        # Register
        task = TaskRequest(task_id="t1", task_type="register_server", payload={
            "name": "test-fs",
            "transport": "stdio",
            "command": "echo",
            "args": ["test"],
            "capabilities": ["filesystem"],
        })
        result = await self.plugin.execute(task)
        assert result.success
        assert result.result["name"] == "test-fs"
        server_id = result.result["id"]

        # List
        task = TaskRequest(task_id="t2", task_type="list_servers", payload={})
        result = await self.plugin.execute(task)
        assert result.success
        assert len(result.result) == 1
        assert result.result[0]["name"] == "test-fs"

        # Unregister
        task = TaskRequest(task_id="t3", task_type="unregister_server", payload={"id": server_id})
        result = await self.plugin.execute(task)
        assert result.success
        assert result.result["removed"] is True

    @pytest.mark.asyncio
    async def test_list_tools(self):
        await self.plugin.initialize({"config_path": self.config_path})
        task = TaskRequest(task_id="t", task_type="list_tools", payload={})
        result = await self.plugin.execute(task)
        assert result.success
        assert result.result == {}

    @pytest.mark.asyncio
    async def test_stats(self):
        await self.plugin.initialize({"config_path": self.config_path})
        task = TaskRequest(task_id="t", task_type="stats", payload={})
        result = await self.plugin.execute(task)
        assert result.success
        assert "servers_total" in result.result
        assert "tools_discovered" in result.result

    @pytest.mark.asyncio
    async def test_unknown_task_type(self):
        await self.plugin.initialize({"config_path": self.config_path})
        task = TaskRequest(task_id="t", task_type="unknown_thing", payload={})
        result = await self.plugin.execute(task)
        assert not result.success
        assert "Unknown task type" in result.error

    @pytest.mark.asyncio
    async def test_shutdown(self):
        await self.plugin.initialize({"config_path": self.config_path})
        await self.plugin.shutdown()
        assert not self.plugin.is_initialized

    @pytest.mark.asyncio
    async def test_registry_persists_after_shutdown(self):
        await self.plugin.initialize({"config_path": self.config_path})

        # Register a server
        task = TaskRequest(task_id="t", task_type="register_server", payload={
            "name": "persist-test",
            "transport": "stdio",
            "command": "echo",
            "capabilities": ["test"],
        })
        await self.plugin.execute(task)

        # Shutdown saves
        await self.plugin.shutdown()

        # Verify file exists and has data
        registry2 = MCPServerRegistry(config_path=self.config_path)
        registry2.load()
        assert registry2.count() == 1
        assert registry2.get_by_name("persist-test") is not None

    @pytest.mark.asyncio
    async def test_call_tool_missing_name(self):
        await self.plugin.initialize({"config_path": self.config_path})
        task = TaskRequest(task_id="t", task_type="call_tool", payload={"arguments": {}})
        result = await self.plugin.execute(task)
        assert not result.success
        assert "Missing tool name" in result.error

    @pytest.mark.asyncio
    async def test_register_server_missing_name(self):
        await self.plugin.initialize({"config_path": self.config_path})
        task = TaskRequest(task_id="t", task_type="register_server", payload={"command": "x"})
        result = await self.plugin.execute(task)
        assert not result.success
        assert "Missing server name" in result.error

    @pytest.mark.asyncio
    async def test_unregister_server_missing_id(self):
        await self.plugin.initialize({"config_path": self.config_path})
        task = TaskRequest(task_id="t", task_type="unregister_server", payload={})
        result = await self.plugin.execute(task)
        assert not result.success
        assert "Missing server ID" in result.error


class TestMCPIntegrationInit:
    """Test that the __init__.py exports work."""

    def test_imports(self):
        from core.mcp_integration import (
            MCPServerRecord,
            MCPServerRegistry,
            MCPToolBridge,
            BridgeStats,
            MCPIntegrationPlugin,
        )
        assert MCPServerRecord is not None
        assert MCPServerRegistry is not None
        assert MCPToolBridge is not None
        assert BridgeStats is not None
        assert MCPIntegrationPlugin is not None

    def test_version(self):
        from core.mcp_integration import __version__
        assert __version__ == "1.0.0"
