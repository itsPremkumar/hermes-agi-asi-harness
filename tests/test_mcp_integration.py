"""Tests for MCP Integration Layer — Server Registry + Tool Bridge."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from core.mcp_integration.server_registry import MCPServerRecord, MCPServerRegistry
from core.mcp_integration.tool_bridge import (
    BridgeError,
    BridgeStats,
    MCPToolBridge,
    ServerConnectionError,
    ToolNotFoundError,
)


# ---------------------------------------------------------------------------
# MCPServerRecord
# ---------------------------------------------------------------------------


class TestMCPServerRecord:
    def test_create_defaults(self):
        record = MCPServerRecord(name="test")
        assert record.name == "test"
        assert record.transport == "stdio"
        assert record.enabled is True
        assert record.health_status == "unknown"
        assert record.capabilities == []
        assert record.args == []

    def test_create_full(self):
        record = MCPServerRecord(
            name="fs",
            transport="stdio",
            command="npx",
            args=["-y", "@mcp/filesystem"],
            capabilities=["filesystem", "read"],
            env={"HOME": "/tmp"},
        )
        assert record.command == "npx"
        assert record.args == ["-y", "@mcp/filesystem"]
        assert "filesystem" in record.capabilities

    def test_serialization_round_trip(self):
        record = MCPServerRecord(
            name="test",
            transport="http",
            url="http://localhost:3000",
            capabilities=["search"],
        )
        d = record.to_dict()
        assert d["name"] == "test"
        assert d["transport"] == "http"

        restored = MCPServerRecord.from_dict(d)
        assert restored.name == "test"
        assert restored.url == "http://localhost:3000"
        assert "search" in restored.capabilities

    def test_from_dict_ignores_extra_fields(self):
        data = {
            "name": "test",
            "extra_field": "should_be_ignored",
            "transport": "stdio",
        }
        record = MCPServerRecord.from_dict(data)
        assert record.name == "test"
        assert not hasattr(record, "extra_field")


# ---------------------------------------------------------------------------
# MCPServerRegistry
# ---------------------------------------------------------------------------


class TestMCPServerRegistry:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.config_path = str(tmp_path / "mcp_servers.json")

    def test_load_missing_file(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        assert registry.load() is False

    def test_register_and_get(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        record = registry.register(
            name="test",
            transport="stdio",
            command="echo",
            capabilities=["test"],
        )
        assert record.id in registry.records
        assert registry.get(record.id) == record
        assert registry.get_by_name("test") == record

    def test_register_duplicate_name_raises(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        registry.register(name="test", command="echo")
        with pytest.raises(ValueError, match="already registered"):
            registry.register(name="test", command="other")

    def test_unregister(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        record = registry.register(name="test", command="echo")
        assert registry.unregister(record.id) is True
        assert registry.get(record.id) is None
        assert registry.get_by_name("test") is None

    def test_unregister_missing(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()
        assert registry.unregister("nonexistent") is False

    def test_update(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        record = registry.register(name="test", command="echo")
        updated = registry.update(record.id, description="updated")
        assert updated.description == "updated"

    def test_update_missing_raises(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()
        with pytest.raises(KeyError):
            registry.update("nonexistent", description="x")

    def test_search(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        registry.register(name="filesystem", command="npx", capabilities=["filesystem", "read"])
        registry.register(name="search", command="curl", capabilities=["search", "web"])

        results = registry.search("file")
        assert len(results) == 1
        assert results[0].name == "filesystem"

        results = registry.search("web")
        assert len(results) == 1
        assert results[0].name == "search"

    def test_get_by_capability(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        r1 = registry.register(name="a", command="x", capabilities=["fs", "read"])
        r2 = registry.register(name="b", command="y", capabilities=["fs", "write"])

        fs_servers = registry.get_by_capability("fs")
        assert len(fs_servers) == 2

        read_servers = registry.get_by_capability("read")
        assert len(read_servers) == 1
        assert read_servers[0].name == "a"

    def test_list_enabled(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        r1 = registry.register(name="a", command="x", capabilities=["fs"])
        r2 = registry.register(name="b", command="y", capabilities=["web"])
        registry.update(r2.id, enabled=False)

        enabled = registry.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "a"

    def test_set_health(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        record = registry.register(name="test", command="echo")
        registry.set_health(record.id, "connected")
        assert registry.get(record.id).health_status == "connected"
        assert registry.get(record.id).last_health_check is not None

    def test_save_and_load(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()

        registry.register(name="a", command="x", capabilities=["fs"])
        registry.register(name="b", command="y", capabilities=["web"])
        registry.save()

        # Load into new instance
        registry2 = MCPServerRegistry(config_path=self.config_path)
        registry2.load()
        assert registry2.count() == 2
        assert registry2.get_by_name("a") is not None
        assert registry2.get_by_name("b") is not None

    def test_load_legacy_list_format(self, tmp_path):
        """Registry files that are plain lists (no wrapper dict) should load."""
        config_path = str(tmp_path / "legacy.json")
        Path(config_path).write_text(
            '[{"name": "legacy", "transport": "stdio", "command": "x", "capabilities": [], "args": [], "env": {}, "metadata": {}}]',
            encoding="utf-8",
        )
        registry = MCPServerRegistry(config_path=config_path)
        registry.load()
        assert registry.count() == 1
        assert registry.get_by_name("legacy") is not None

    def test_count(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()
        assert registry.count() == 0

        registry.register(name="a", command="x")
        assert registry.count() == 1

    def test_to_dict(self):
        registry = MCPServerRegistry(config_path=self.config_path)
        registry.load()
        registry.register(name="a", command="x", capabilities=["fs"])

        d = registry.to_dict()
        assert "version" in d
        assert "servers" in d
        assert len(d["servers"]) == 1


# ---------------------------------------------------------------------------
# BridgeStats
# ---------------------------------------------------------------------------


class TestBridgeStats:
    def test_defaults(self):
        stats = BridgeStats()
        assert stats.servers_total == 0
        assert stats.servers_connected == 0
        assert stats.tools_discovered == 0

    def test_to_dict(self):
        stats = BridgeStats(servers_total=5, tools_discovered=10)
        d = stats.to_dict()
        assert d["servers_total"] == 5
        assert d["tools_discovered"] == 10


# ---------------------------------------------------------------------------
# MCPToolBridge (no real MCP server needed)
# ---------------------------------------------------------------------------


class TestMCPToolBridge:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.config_path = str(tmp_path / "mcp_servers.json")
        self.registry = MCPServerRegistry(config_path=self.config_path)
        self.registry.load()
        self.bridge = MCPToolBridge(registry=self.registry)

    def test_init(self):
        assert self.bridge.stats.servers_total == 0
        assert self.bridge.stats.tools_discovered == 0

    def test_available_tools_empty(self):
        assert self.bridge.available_tools() == {}

    def test_find_server_for_tool_none(self):
        assert self.bridge.find_server_for_tool("nonexistent") is None

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        with pytest.raises(ToolNotFoundError):
            await self.bridge.call_tool("nonexistent", {})

    @pytest.mark.asyncio
    async def test_disconnect_all_empty(self):
        await self.bridge.disconnect_all()  # should not raise

    @pytest.mark.asyncio
    async def test_connect_server_missing(self):
        with pytest.raises(KeyError):
            await self.bridge.connect_server("nonexistent-id")

    def test_repr(self):
        r = repr(self.bridge)
        assert "MCPToolBridge" in r
