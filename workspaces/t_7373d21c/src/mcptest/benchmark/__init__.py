"""Performance benchmark runner for MCP servers."""

from __future__ import annotations

import asyncio
import random
import statistics
import time
from typing import Any, Optional

import httpx

from mcptest.config import Config
from mcptest.models import (
    BenchmarkResult,
    TestResult,
    TestStatus,
    TestSuite,
)
from mcptest.client import MockMCPClient


class BenchmarkRunner:
    """Benchmarks MCP server performance.

    Measures throughput, latency percentiles, and memory usage
    under configurable concurrency.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = MockMCPClient(config)
        self.duration = config.benchmark_duration_seconds
        self.concurrency = config.benchmark_concurrency

    async def run(self) -> BenchmarkResult:
        """Execute the benchmark suite."""
        suite = TestSuite(name="MCP Benchmark")

        tests = [
            self._test_throughput,
            self._test_latency,
            self._test_concurrency,
            self._test_memory,
        ]

        for test_fn in tests:
            result = await test_fn()
            suite.results.append(result)

        suite.finished_at = __import__("datetime").datetime.utcnow()

        # Aggregate results
        latencies: list[float] = []
        total_requests = 0
        failed_requests = 0
        peak_memory = 0.0

        for r in suite.results:
            if "latencies" in r.details:
                latencies.extend(r.details["latencies"])
            if "total_requests" in r.details:
                total_requests += r.details["total_requests"]
            if "failed_requests" in r.details:
                failed_requests += r.details["failed_requests"]
            if "peak_memory_mb" in r.details:
                peak_memory = max(peak_memory, r.details["peak_memory_mb"])

        avg_latency = statistics.mean(latencies) if latencies else 0.0
        p50 = statistics.median(latencies) if latencies else 0.0
        p95 = self._percentile(latencies, 95) if latencies else 0.0
        p99 = self._percentile(latencies, 99) if latencies else 0.0
        rps = total_requests / self.duration if self.duration > 0 else 0.0

        return BenchmarkResult(
            suite=suite,
            requests_per_second=rps,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            peak_memory_mb=peak_memory,
            total_requests=total_requests,
            failed_requests=failed_requests,
        )

    @staticmethod
    def _percentile(data: list[float], pct: int) -> float:
        """Calculate the given percentile using nearest-rank method."""
        if not data:
            return 0.0
        import math
        sorted_data = sorted(data)
        idx = math.ceil(len(sorted_data) * pct / 100) - 1
        return sorted_data[max(0, idx)]

    async def _test_throughput(self) -> TestResult:
        """Measure requests per second."""
        start = time.monotonic()
        count = 0
        errors = 0
        latencies: list[float] = []

        deadline = start + min(self.duration, 10)
        while time.monotonic() < deadline:
            t0 = time.monotonic()
            try:
                await self.client.list_tools()
                latencies.append((time.monotonic() - t0) * 1000)
                count += 1
            except Exception:
                errors += 1

        duration = time.monotonic() - start
        rps = count / duration if duration > 0 else 0

        # Check threshold
        threshold = self.config.thresholds.min_requests_per_second
        status = TestStatus.PASS if rps >= threshold else TestStatus.FAIL

        return TestResult(
            name="throughput",
            status=status,
            duration_ms=duration * 1000,
            message=f"{rps:.1f} req/s (threshold: {threshold:.1f})",
            details={
                "total_requests": count,
                "failed_requests": errors,
                "latencies": latencies,
                "rps": rps,
            },
        )

    async def _test_latency(self) -> TestResult:
        """Measure latency percentiles."""
        start = time.monotonic()
        latencies: list[float] = []
        count = 0

        deadline = start + min(self.duration, 10)
        while time.monotonic() < deadline:
            t0 = time.monotonic()
            try:
                await self.client.ping()
                latencies.append((time.monotonic() - t0) * 1000)
                count += 1
            except Exception:
                pass

        duration = time.monotonic() - start
        avg = statistics.mean(latencies) if latencies else 0.0
        p50 = statistics.median(latencies) if latencies else 0.0
        p95 = self._percentile(latencies, 95) if latencies else 0.0
        p99 = self._percentile(latencies, 99) if latencies else 0.0

        threshold = self.config.thresholds.max_avg_latency_ms
        status = TestStatus.PASS if avg <= threshold else TestStatus.FAIL

        return TestResult(
            name="latency",
            status=status,
            duration_ms=duration * 1000,
            message=f"avg={avg:.1f}ms p50={p50:.1f}ms p95={p95:.1f}ms p99={p99:.1f}ms",
            details={
                "total_requests": count,
                "latencies": latencies,
            },
        )

    async def _test_concurrency(self) -> TestResult:
        """Test under concurrent load."""
        start = time.monotonic()
        count = 0
        errors = 0
        latencies: list[float] = []

        async def worker():
            nonlocal count, errors
            deadline = time.monotonic() + min(self.duration, 5)
            while time.monotonic() < deadline:
                t0 = time.monotonic()
                try:
                    await self.client.list_tools()
                    latencies.append((time.monotonic() - t0) * 1000)
                    count += 1
                except Exception:
                    errors += 1

        await asyncio.gather(*[worker() for _ in range(self.concurrency)])
        duration = time.monotonic() - start
        rps = count / duration if duration > 0 else 0

        return TestResult(
            name="concurrency",
            status=TestStatus.PASS if errors == 0 else TestStatus.FAIL,
            duration_ms=duration * 1000,
            message=f"{count} requests across {self.concurrency} workers, {errors} errors",
            details={
                "total_requests": count,
                "failed_requests": errors,
                "latencies": latencies,
            },
        )

    async def _test_memory(self) -> TestResult:
        """Measure memory usage."""
        start = time.monotonic()

        try:
            import tracemalloc
            tracemalloc.start()

            # Run requests to trigger memory allocation
            for _ in range(100):
                try:
                    await self.client.list_tools()
                except Exception:
                    pass

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            peak_mb = peak / 1024 / 1024
            duration = time.monotonic() - start

            threshold = self.config.thresholds.max_memory_mb
            status = TestStatus.PASS if peak_mb <= threshold else TestStatus.FAIL

            return TestResult(
                name="memory",
                status=status,
                duration_ms=duration * 1000,
                message=f"Peak memory: {peak_mb:.1f} MB (threshold: {threshold:.1f} MB)",
                details={
                    "peak_memory_mb": peak_mb,
                    "total_requests": 100,
                    "failed_requests": 0,
                },
            )
        except ImportError:
            duration = time.monotonic() - start
            return TestResult(
                name="memory",
                status=TestStatus.SKIP,
                duration_ms=duration * 1000,
                message="tracemalloc not available",
            )
