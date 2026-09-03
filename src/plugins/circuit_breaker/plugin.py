"""circuit_breaker — re-export module."""
from . import (
    CircuitBreakerPlugin,
    CircuitBreakerConfig,
    PlaneHealth,
    CircuitState,
    register_fallback,
    get_fallbacks,
)
from .health import HealthMonitor
from .recovery import RecoveryEngine, RecoveryResult, Checkpoint

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
