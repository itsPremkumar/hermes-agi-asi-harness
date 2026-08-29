"""Tests for AgentOS resource governor module."""

from __future__ import annotations

import time

import pytest

from agentos.governor import (
    RateLimiter,
    ResourceGovernor,
    ResourceLimits,
    ResourceUsage,
)


class TestRateLimiter:
    def test_allows_within_limit(self) -> None:
        limiter = RateLimiter(max_requests=5, window_seconds=60.0)
        for _ in range(5):
            assert limiter.allow() is True
            limiter.record()

    def test_blocks_over_limit(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=60.0)
        limiter.record()
        limiter.record()
        assert limiter.allow() is False

    def test_remaining_count(self) -> None:
        limiter = RateLimiter(max_requests=5, window_seconds=60.0)
        limiter.record()
        limiter.record()
        assert limiter.remaining() == 3

    def test_reset(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=60.0)
        limiter.record()
        limiter.record()
        limiter.reset()
        assert limiter.allow() is True
        assert limiter.remaining() == 2

    def test_window_expiration(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=0.1)
        limiter.record()
        limiter.record()
        assert limiter.allow() is False
        time.sleep(0.15)
        assert limiter.allow() is True


class TestResourceGovernor:
    def test_register_tenant(self) -> None:
        governor = ResourceGovernor()
        governor.register_tenant("t1")
        assert governor.get_usage("t1") is not None

    def test_allocate_cpu_within_limit(self) -> None:
        governor = ResourceGovernor(ResourceLimits(max_cpu=2.0))
        governor.register_tenant("t1")
        assert governor.allocate_cpu("t1", 1.0) is True
        assert governor.get_usage("t1").cpu == 1.0

    def test_reject_cpu_over_limit(self) -> None:
        governor = ResourceGovernor(ResourceLimits(max_cpu=2.0))
        governor.register_tenant("t1")
        assert governor.allocate_cpu("t1", 3.0) is False

    def test_release_cpu(self) -> None:
        governor = ResourceGovernor(ResourceLimits(max_cpu=2.0))
        governor.register_tenant("t1")
        governor.allocate_cpu("t1", 1.5)
        governor.release_cpu("t1", 0.5)
        assert governor.get_usage("t1").cpu == 1.0

    def test_allocate_memory_within_limit(self) -> None:
        governor = ResourceGovernor(ResourceLimits(max_memory=1024))
        governor.register_tenant("t1")
        assert governor.allocate_memory("t1", 512) is True

    def test_reject_memory_over_limit(self) -> None:
        governor = ResourceGovernor(ResourceLimits(max_memory=1024))
        governor.register_tenant("t1")
        assert governor.allocate_memory("t1", 2048) is False

    def test_release_memory(self) -> None:
        governor = ResourceGovernor(ResourceLimits(max_memory=1024))
        governor.register_tenant("t1")
        governor.allocate_memory("t1", 512)
        governor.release_memory("t1", 256)
        assert governor.get_usage("t1").memory == 256

    def test_api_rate_limiting(self) -> None:
        governor = ResourceGovernor(ResourceLimits(max_api_requests_per_minute=2))
        governor.register_tenant("t1")
        assert governor.record_api_request("t1") is True
        assert governor.record_api_request("t1") is True
        assert governor.record_api_request("t1") is False

    def test_unknown_tenant(self) -> None:
        governor = ResourceGovernor()
        assert governor.get_usage("unknown") is None
        assert governor.allocate_cpu("unknown", 1.0) is False

    def test_violation_hook(self) -> None:
        violations: list[tuple[str, str]] = []
        governor = ResourceGovernor(ResourceLimits(max_cpu=1.0))
        governor.add_hook(lambda tid, reason: violations.append((tid, reason)))
        governor.register_tenant("t1")
        governor.allocate_cpu("t1", 2.0)  # This fails but doesn't trigger hook
        # Hook is for future use when we add enforcement notifications
        assert len(violations) == 0  # No hooks called on allocation failure yet
