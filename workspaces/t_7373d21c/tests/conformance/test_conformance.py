"""Tests for MCPTest conformance module."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcptest.config import Config, ServerTarget
from mcptest.conformance import ConformanceTester
from mcptest.models import TestStatus


@pytest.fixture
def config():
    return Config(
        target=ServerTarget(name="test-server", transport="stdio"),
    )


@pytest.fixture
def tester(config):
    return ConformanceTester(config)


class TestConformanceTester:
    """Tests for the conformance test suite."""

    @pytest.mark.asyncio
    async def test_init_success(self, tester):
        with patch.object(
            tester.client,
            "initialize",
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "serverInfo": {"name": "test", "version": "1.0.0"},
                },
            },
        ):
            result = await tester._test_init()
            assert result.status == TestStatus.PASS
            assert result.name == "init"

    @pytest.mark.asyncio
    async def test_init_failure(self, tester):
        with patch.object(
            tester.client,
            "initialize",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid"}},
        ):
            result = await tester._test_init()
            assert result.status == TestStatus.FAIL

    @pytest.mark.asyncio
    async def test_init_response_schema_valid(self, tester):
        with patch.object(
            tester.client,
            "initialize",
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "serverInfo": {"name": "test", "version": "1.0.0"},
                },
            },
        ):
            result = await tester._test_initialize_response_schema()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_init_response_schema_missing_field(self, tester):
        with patch.object(
            tester.client,
            "initialize",
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"protocolVersion": "2024-11-05"},
            },
        ):
            result = await tester._test_initialize_response_schema()
            assert result.status == TestStatus.FAIL
            assert "Missing fields" in result.message

    @pytest.mark.asyncio
    async def test_tools_list_success(self, tester):
        with patch.object(
            tester.client,
            "list_tools",
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"tools": [{"name": "echo", "description": "Echo tool"}]},
            },
        ):
            result = await tester._test_tools_list()
            assert result.status == TestStatus.PASS
            assert "1 tools" in result.message

    @pytest.mark.asyncio
    async def test_tools_list_empty(self, tester):
        with patch.object(
            tester.client,
            "list_tools",
            return_value={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
        ):
            result = await tester._test_tools_list()
            assert result.status == TestStatus.PASS
            assert "0 tools" in result.message

    @pytest.mark.asyncio
    async def test_idempotency_pass(self, tester):
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": [{"name": "echo"}]},
        }
        with patch.object(tester.client, "list_tools", return_value=response):
            result = await tester._test_idempotency()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_error_unknown_method(self, tester):
        with patch.object(
            tester.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}},
        ):
            result = await tester._test_error_unknown_method()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_ping(self, tester):
        with patch.object(
            tester.client,
            "ping",
            return_value={"jsonrpc": "2.0", "id": 1, "result": {}},
        ):
            result = await tester._test_ping()
            assert result.status == TestStatus.PASS
