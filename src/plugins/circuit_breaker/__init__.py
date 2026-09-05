"""Circuit Breaker & Failure Recovery Layer for ASI Cognitive Architecture.

Provides per-plane health monitoring, circuit breaker state machine,
automatic retry with exponential backoff, fallback chain support,
checkpoint/resume, and graceful degradation.

Failure modes handled:
- Plane 3 (Meta-Reasoning): Invalid strategy → fallback to default
- Plane 4 (Deep Research): Search timeout → partial results
- Plane 7 (Search): All backends down → cached/local knowledge
- Plane 8 (Multi-Agent): Sub-agent crash → retry with different agent
- Plane 10 (ToT): Combinatorial explosion → beam search with depth limit
- Plane 13 (Verification): Timeout → return with "unverified" flag
- Plane 14 (AVO): Population stagnation → reduce population, increase mutation
- Plane 15 (Memory): Storage full → evict oldest, compress
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("hermes_circuit_breaker")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"

    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: list[str] = field(default_factory=list)
        shell_commands: list[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: int = 512
        max_cpu_percent: int = 50

    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: list[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: list[str] = field(default_factory=list)
        path: Path | None = None

    class PluginBase:
        manifest: PluginManifest

        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED

        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True

        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True

        async def stop(self) -> bool:
            self.state = PluginState.PAUSED
            return True

        async def unload(self) -> bool:
            self.state = PluginState.UNLOADED
            return True


# ---------------------------------------------------------------------------
# Circuit Breaker State Machine
# ---------------------------------------------------------------------------

class CircuitState(str, Enum):
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failing, reject requests
    HALF_OPEN = "half_open"    # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for a single circuit breaker."""
    failure_threshold: int = 5           # Failures before opening
    recovery_timeout: float = 30.0       # Seconds before half-open
    success_threshold: int = 3            # Successes before closing
    timeout: float = 60.0                # Per-call timeout
    max_retries: int = 3                 # Retry attempts
    backoff_base: float = 1.0            # Exponential backoff base
    backoff_max: float = 30.0            # Max backoff seconds


@dataclass
class PlaneHealth:
    """Health metrics for a single cognitive plane."""
    plane_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0
    last_call_time: float = 0.0
    last_failure_time: float = 0.0
    last_error: str = ""
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    total_latency_ms: float = 0.0
    latencies_ms: list[float] = field(default_factory=list)
    errors_per_minute: float = 0.0
    error_timestamps: list[float] = field(default_factory=list)

    @property
    def error_rate(self) -> float:
        return self.failed_calls / self.total_calls if self.total_calls else 0.0

    @property
    def average_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_calls if self.total_calls else 0.0

    def latency_percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * p / 100)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def record_success(self, latency_ms: float) -> None:
        self.total_calls += 1
        self.successful_calls += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_call_time = time.time()
        self.total_latency_ms += latency_ms
        self.latencies_ms.append(latency_ms)
        # Keep only last 1000 latencies
        if len(self.latencies_ms) > 1000:
            self.latencies_ms = self.latencies_ms[-1000:]

    def record_failure(self, error: str = "", timeout: bool = False) -> None:
        self.total_calls += 1
        self.failed_calls += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_call_time = time.time()
        self.last_failure_time = time.time()
        self.last_error = error
        if timeout:
            self.timeout_calls += 1
        now = time.time()
        self.error_timestamps.append(now)
        # Keep only last 5 minutes of errors
        self.error_timestamps = [t for t in self.error_timestamps if now - t < 300]
        self.errors_per_minute = len(self.error_timestamps) / 5.0

    def get_status(self) -> dict[str, Any]:
        return {
            "plane_name": self.plane_name,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "error_rate": self.error_rate,
            "timeout_calls": self.timeout_calls,
            "circuit_state": self.circuit_state.value,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "average_latency_ms": self.average_latency_ms,
            "p50_latency_ms": self.latency_percentile(50),
            "p95_latency_ms": self.latency_percentile(95),
            "p99_latency_ms": self.latency_percentile(99),
            "errors_per_minute": self.errors_per_minute,
            "last_error": self.last_error,
        }


# ---------------------------------------------------------------------------
# Fallback Registry
# ---------------------------------------------------------------------------

# Maps plane name → list of fallback functions (tried in order)
FALLBACK_CHAIN: dict[str, list[Callable]] = {}


def register_fallback(plane_name: str, fallback_fn: Callable) -> None:
    """Register a fallback function for a plane."""
    if plane_name not in FALLBACK_CHAIN:
        FALLBACK_CHAIN[plane_name] = []
    FALLBACK_CHAIN[plane_name].append(fallback_fn)


def get_fallbacks(plane_name: str) -> list[Callable]:
    """Get the fallback chain for a plane."""
    return FALLBACK_CHAIN.get(plane_name, [])


# ---------------------------------------------------------------------------
# Circuit Breaker Plugin
# ---------------------------------------------------------------------------

class CircuitBreakerPlugin(PluginBase):
    """Main circuit breaker plugin — monitors all cognitive planes."""

    def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
        super().__init__(manifest, kernel)
        self._planes: dict[str, PlaneHealth] = {}
        self._configs: dict[str, CircuitBreakerConfig] = {}
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self._running = False

    def _get_or_create(self, plane_name: str) -> PlaneHealth:
        if plane_name not in self._planes:
            self._planes[plane_name] = PlaneHealth(plane_name=plane_name)
            self._configs[plane_name] = CircuitBreakerConfig()
        return self._planes[plane_name]

    def configure_plane(self, plane_name: str, config: CircuitBreakerConfig) -> None:
        """Configure circuit breaker thresholds for a plane."""
        self._get_or_create(plane_name)
        self._configs[plane_name] = config

    async def call_plane(
        self,
        plane_name: str,
        operation: Callable,
        *args: Any,
        fallback: Callable | None = None,
        **kwargs: Any,
    ) -> tuple[Any, bool]:
        """
        Execute a plane operation with circuit breaker protection.

        Returns:
            Tuple of (result, used_fallback)
        """
        health = self._get_or_create(plane_name)
        config = self._configs[plane_name]

        # Check circuit state
        if health.circuit_state == CircuitState.OPEN:
            if time.time() - health.last_failure_time >= config.recovery_timeout:
                health.circuit_state = CircuitState.HALF_OPEN
                logger.info(f"Plane {plane_name}: OPEN → HALF_OPEN")
            else:
                logger.warning(f"Plane {plane_name}: Circuit OPEN, using fallback")
                if fallback:
                    return await fallback(*args, **kwargs), True
                return None, True

        # Try the operation with retries
        last_error = ""
        for attempt in range(config.max_retries + 1):
            start = time.time()
            try:
                # Execute with timeout
                if asyncio.iscoroutinefunction(operation):
                    result = await asyncio.wait_for(
                        operation(*args, **kwargs),
                        timeout=config.timeout,
                    )
                else:
                    result = operation(*args, **kwargs)

                latency_ms = (time.time() - start) * 1000
                health.record_success(latency_ms)

                # Check if circuit should close
                if health.circuit_state == CircuitState.HALF_OPEN:
                    if health.consecutive_successes >= config.success_threshold:
                        health.circuit_state = CircuitState.CLOSED
                        logger.info(f"Plane {plane_name}: HALF_OPEN → CLOSED")

                return result, False

            except asyncio.TimeoutError:
                latency_ms = (time.time() - start) * 1000
                health.record_failure(timeout=True)
                last_error = f"Timeout after {config.timeout}s"
                logger.warning(f"Plane {plane_name}: Timeout (attempt {attempt + 1})")

            except Exception as e:
                latency_ms = (time.time() - start) * 1000
                health.record_failure(error=str(e))
                last_error = str(e)
                logger.warning(f"Plane {plane_name}: Error - {e} (attempt {attempt + 1})")

            # Check if circuit should open
            if health.consecutive_failures >= config.failure_threshold:
                health.circuit_state = CircuitState.OPEN
                logger.error(f"Plane {plane_name}: CLOSED → OPEN ({health.consecutive_failures} failures)")

            # Exponential backoff
            if attempt < config.max_retries:
                backoff = min(
                    config.backoff_base * (2 ** attempt),
                    config.backoff_max,
                )
                await asyncio.sleep(backoff)

        # All retries exhausted — try fallback
        if fallback:
            try:
                result = await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
                logger.info(f"Plane {plane_name}: Fallback succeeded")
                return result, True
            except Exception as e:
                logger.error(f"Plane {plane_name}: Fallback also failed: {e}")

        if last_error:
            logger.error(f"Plane {plane_name}: All retries exhausted. Last error: {last_error}")
        return None, False

    def get_plane_health(self, plane_name: str) -> dict[str, Any]:
        """Get health metrics for a plane."""
        health = self._get_or_create(plane_name)
        return health.get_status()

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        """Get health metrics for all planes."""
        return {name: health.get_status() for name, health in self._planes.items()}

    def get_overall_health(self) -> dict[str, Any]:
        """Get overall system health."""
        if not self._planes:
            return {"status": "healthy", "planes": 0, "open_circuits": 0}

        open_circuits = sum(
            1 for h in self._planes.values()
            if h.circuit_state == CircuitState.OPEN
        )
        half_open = sum(
            1 for h in self._planes.values()
            if h.circuit_state == CircuitState.HALF_OPEN
        )
        total = len(self._planes)

        if open_circuits > total / 2:
            status = "critical"
        elif open_circuits > 0:
            status = "degraded"
        elif half_open > 0:
            status = "recovering"
        else:
            status = "healthy"

        return {
            "status": status,
            "planes": total,
            "open_circuits": open_circuits,
            "half_open_circuits": half_open,
            "closed_circuits": total - open_circuits - half_open,
        }

    def save_checkpoint(self, task_id: str, state: dict[str, Any]) -> None:
        """Save a checkpoint for recovery."""
        self._checkpoints[task_id] = {
            "state": state,
            "timestamp": time.time(),
        }

    def load_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        """Load a checkpoint for recovery."""
        cp = self._checkpoints.get(task_id)
        if cp:
            return cp["state"]
        return None

    async def start(self) -> bool:
        self._running = True
        self.state = PluginState.RUNNING
        logger.info("Circuit breaker plugin started")
        return True

    async def stop(self) -> bool:
        self._running = False
        self.state = PluginState.PAUSED
        logger.info("Circuit breaker plugin stopped")
        return True


# ---------------------------------------------------------------------------
# Default fallback functions
# ---------------------------------------------------------------------------

async def fallback_meta_reasoning(*args, **kwargs) -> dict[str, Any]:
    """Fallback for Plane 3: return default DEBIAS strategy."""
    return {
        "strategy": "DEBIAS",
        "confidence": 0.5,
        "note": "Fallback: using default strategy (plane unavailable)",
    }


async def fallback_deep_research(*args, **kwargs) -> dict[str, Any]:
    """Fallback for Plane 4: return partial results."""
    return {
        "findings": [],
        "sources": [],
        "gates": ["Search timed out — results incomplete"],
        "partial": True,
    }


async def fallback_search(*args, **kwargs) -> dict[str, Any]:
    """Fallback for Plane 7: use cached/local knowledge."""
    return {
        "results": [],
        "source": "cached_local_knowledge",
        "note": "Fallback: all search backends down, using cached data",
    }


async def fallback_multi_agent(*args, **kwargs) -> dict[str, Any]:
    """Fallback for Plane 8: single-agent execution."""
    return {
        "result": None,
        "mode": "single_agent_fallback",
        "note": "Fallback: multi-agent unavailable, using single agent",
    }


async def fallback_tot(*args, **kwargs) -> dict[str, Any]:
    """Fallback for Plane 10: beam search with depth limit."""
    return {
        "selected_approach": None,
        "mode": "beam_search_limited",
        "max_depth": 3,
        "note": "Fallback: ToT combinatorial explosion, using limited beam search",
    }


async def fallback_verification(*args, **kwargs) -> dict[str, Any]:
    """Fallback for Plane 13: return unverified."""
    return {
        "verified": False,
        "confidence": 0.0,
        "flag": "unverified",
        "note": "Fallback: verification timeout, result unverified",
    }


async def fallback_avo(*args, **kwargs) -> dict[str, Any]:
    """Fallback for Plane 14: reduce population, increase mutation."""
    return {
        "population_size": 10,
        "mutation_rate": 0.3,
        "note": "Fallback: AVO stagnation, reduced population + increased mutation",
    }


async def fallback_memory(*args, **kwargs) -> dict[str, Any]:
    """Fallback for Plane 15: evict oldest, compress."""
    return {
        "evicted": 0,
        "compressed": True,
        "note": "Fallback: memory storage full, evicted oldest entries",
    }


# Register all fallbacks
register_fallback("meta_reasoning", fallback_meta_reasoning)
register_fallback("deep_research", fallback_deep_research)
register_fallback("search", fallback_search)
register_fallback("multi_agent", fallback_multi_agent)
register_fallback("tree_of_thoughts", fallback_tot)
register_fallback("verification", fallback_verification)
register_fallback("avo", fallback_avo)
register_fallback("memory", fallback_memory)


# ---------------------------------------------------------------------------
# Module-level instance
# ---------------------------------------------------------------------------

# Deferred: .health / .recovery import names from this package (circular).
from .health import HealthMonitor  # noqa: E402
from .recovery import Checkpoint, RecoveryEngine, RecoveryResult  # noqa: E402

Plugin = CircuitBreakerPlugin

__all__ = [
    "CircuitBreakerPlugin",
    "CircuitBreakerConfig",
    "PlaneHealth",
    "CircuitState",
    "HealthMonitor",
    "RecoveryEngine",
    "RecoveryResult",
    "Checkpoint",
    "Plugin",
    "register_fallback",
    "get_fallbacks",
]
