"""Resource governor for CPU, memory, and API rate limits."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable


@dataclass
class ResourceLimits:
    """Resource limits for a tenant or agent."""
    max_cpu: float = 4.0  # CPU cores
    max_memory: int = 8192  # MB
    max_api_requests_per_minute: int = 60
    max_concurrent_agents: int = 4
    max_agents_per_tenant: int = 10


@dataclass
class ResourceUsage:
    """Current resource usage."""
    cpu: float = 0.0
    memory: int = 0
    api_requests: int = 0
    api_window_start: float = 0.0
    concurrent_agents: int = 0
    total_agents: int = 0


class RateLimiter:
    """Token-bucket rate limiter with sliding window."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: list[float] = []
        self._lock = Lock()

    def allow(self) -> bool:
        """Check if a request is allowed."""
        with self._lock:
            now = time.monotonic()
            # Remove expired timestamps
            cutoff = now - self.window_seconds
            self._requests = [t for t in self._requests if t > cutoff]
            return len(self._requests) < self.max_requests

    def record(self) -> None:
        """Record a request."""
        with self._lock:
            self._requests.append(time.monotonic())

    def remaining(self) -> int:
        """Get remaining requests in current window."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            self._requests = [t for t in self._requests if t > cutoff]
            return max(0, self.max_requests - len(self._requests))

    def reset(self) -> None:
        """Reset the rate limiter."""
        with self._lock:
            self._requests.clear()


class ResourceGovernor:
    """Governs resource allocation and enforces limits."""

    def __init__(self, limits: ResourceLimits | None = None) -> None:
        self.limits = limits or ResourceLimits()
        self._usage: dict[str, ResourceUsage] = {}
        self._tenant_limits: dict[str, ResourceLimits] = {}
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._lock = Lock()
        self._hooks: list[Callable[[str, str], None]] = []

    def register_tenant(self, tenant_id: str,
                        limits: ResourceLimits | None = None) -> None:
        """Register a tenant with optional custom limits."""
        with self._lock:
            if tenant_id not in self._usage:
                self._usage[tenant_id] = ResourceUsage()
                tenant_limits = limits or self.limits
                self._tenant_limits[tenant_id] = tenant_limits
                self._rate_limiters[tenant_id] = RateLimiter(
                    tenant_limits.max_api_requests_per_minute
                )

    def _get_tenant_limit(self, tenant_id: str, attr: str) -> float | int:
        """Get a specific limit for a tenant."""
        limits = self._tenant_limits.get(tenant_id, self.limits)
        return getattr(limits, attr)

    def check_cpu(self, tenant_id: str, requested: float) -> bool:
        """Check if CPU allocation is allowed."""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage is None:
                return False
            max_cpu = self._get_tenant_limit(tenant_id, "max_cpu")
            return usage.cpu + requested <= max_cpu

    def allocate_cpu(self, tenant_id: str, amount: float) -> bool:
        """Allocate CPU cores to a tenant."""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage is None:
                return False
            max_cpu = self._get_tenant_limit(tenant_id, "max_cpu")
            if usage.cpu + amount > max_cpu:
                return False
            usage.cpu += amount
            return True

    def release_cpu(self, tenant_id: str, amount: float) -> None:
        """Release CPU cores from a tenant."""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage:
                usage.cpu = max(0.0, usage.cpu - amount)

    def check_memory(self, tenant_id: str, requested: int) -> bool:
        """Check if memory allocation is allowed."""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage is None:
                return False
            max_memory = self._get_tenant_limit(tenant_id, "max_memory")
            return usage.memory + requested <= max_memory

    def allocate_memory(self, tenant_id: str, amount: int) -> bool:
        """Allocate memory to a tenant."""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage is None:
                return False
            max_memory = self._get_tenant_limit(tenant_id, "max_memory")
            if usage.memory + amount > max_memory:
                return False
            usage.memory += amount
            return True

    def release_memory(self, tenant_id: str, amount: int) -> None:
        """Release memory from a tenant."""
        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage:
                usage.memory = max(0, usage.memory - amount)

    def check_api_rate(self, tenant_id: str) -> bool:
        """Check if API request is within rate limit."""
        limiter = self._rate_limiters.get(tenant_id)
        if limiter is None:
            return False
        return limiter.allow()

    def record_api_request(self, tenant_id: str) -> bool:
        """Record an API request if allowed."""
        limiter = self._rate_limiters.get(tenant_id)
        if limiter is None:
            return False
        if limiter.allow():
            limiter.record()
            return True
        return False

    def get_usage(self, tenant_id: str) -> ResourceUsage | None:
        """Get current usage for a tenant."""
        return self._usage.get(tenant_id)

    def add_hook(self, hook: Callable[[str, str], None]) -> None:
        """Add a hook called on limit violations. Hook receives (tenant_id, reason)."""
        self._hooks.append(hook)

    def _notify_violation(self, tenant_id: str, reason: str) -> None:
        """Notify all hooks of a limit violation."""
        for hook in self._hooks:
            try:
                hook(tenant_id, reason)
            except Exception:
                pass  # Hooks should not break governor
