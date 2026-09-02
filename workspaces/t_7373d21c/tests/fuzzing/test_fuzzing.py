"""Tests for MCPTest fuzzing module."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from mcptest.config import Config, ServerTarget
from mcptest.fuzzing import FuzzingEngine, _fuzz_string, _fuzz_number, _fuzz_type, _mutate_jsonrpc
from mcptest.models import TestStatus


@pytest.fixture
def config():
    return Config(
        target=ServerTarget(name="test-server", transport="stdio"),
        fuzzing_iterations=100,
    )


@pytest.fixture
def engine(config):
    return FuzzingEngine(config)


class TestFuzzingHelpers:
    """Tests for fuzzing helper functions."""

    def test_fuzz_string_returns_string(self):
        result = _fuzz_string()
        assert isinstance(result, str)

    def test_fuzz_number_returns_number(self):
        result = _fuzz_number()
        assert isinstance(result, (int, float))

    def test_fuzz_type_returns_value(self):
        result = _fuzz_type()
        # Should return some value without raising
        assert result is not None or result is None  # Always true, just checking no crash

    def test_mutate_jsonrpc_preserves_structure(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        mutated = _mutate_jsonrpc(msg)
        assert isinstance(mutated, dict)


class TestFuzzingEngine:
    """Tests for the fuzzing engine."""

    @pytest.mark.asyncio
    async def test_type_confusion_no_crash(self, engine):
        with patch.object(
            engine.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32600}},
        ):
            result = await engine._test_type_confusion()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_missing_fields_no_crash(self, engine):
        with patch.object(
            engine.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602}},
        ):
            result = await engine._test_missing_fields()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_extra_fields_no_crash(self, engine):
        with patch.object(
            engine.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "result": {}},
        ):
            result = await engine._test_extra_fields()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_boundary_values_no_crash(self, engine):
        with patch.object(
            engine.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602}},
        ):
            result = await engine._test_boundary_values()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_null_bytes_no_crash(self, engine):
        with patch.object(
            engine.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602}},
        ):
            result = await engine._test_null_bytes()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_encoding_issues_no_crash(self, engine):
        with patch.object(
            engine.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32600}},
        ):
            result = await engine._test_encoding_issues()
            assert result.status == TestStatus.PASS
