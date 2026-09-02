"""Tests for MCPTest benchmark module."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from mcptest.config import Config, ServerTarget
from mcptest.benchmark import BenchmarkRunner
from mcptest.models import TestStatus


@pytest.fixture
def config():
    return Config(
        target=ServerTarget(name="test-server", transport="stdio"),
        benchmark_duration_seconds=1,
        benchmark_concurrency=2,
    )


@pytest.fixture
def runner(config):
    return BenchmarkRunner(config)


class TestBenchmarkRunner:
    """Tests for the benchmark runner."""

    def test_percentile_calculation(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        assert BenchmarkRunner._percentile(data, 50) == 5.0
        assert BenchmarkRunner._percentile(data, 95) == 10.0
        assert BenchmarkRunner._percentile(data, 99) == 10.0

    def test_percentile_empty(self):
        assert BenchmarkRunner._percentile([], 50) == 0.0

    @pytest.mark.asyncio
    async def test_throughput(self, runner):
        with patch.object(
            runner.client,
            "list_tools",
            return_value={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
        ):
            result = await runner._test_throughput()
            assert result.name == "throughput"
            assert result.status in (TestStatus.PASS, TestStatus.FAIL)

    @pytest.mark.asyncio
    async def test_latency(self, runner):
        with patch.object(
            runner.client,
            "ping",
            return_value={"jsonrpc": "2.0", "id": 1, "result": {}},
        ):
            result = await runner._test_latency()
            assert result.name == "latency"
            assert result.status in (TestStatus.PASS, TestStatus.FAIL)

    @pytest.mark.asyncio
    async def test_concurrency(self, runner):
        with patch.object(
            runner.client,
            "list_tools",
            return_value={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
        ):
            result = await runner._test_concurrency()
            assert result.name == "concurrency"
            assert result.status in (TestStatus.PASS, TestStatus.FAIL)
