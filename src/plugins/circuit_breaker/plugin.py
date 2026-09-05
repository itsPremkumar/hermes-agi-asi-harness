"""circuit_breaker — re-export module."""
from . import (
    CircuitBreakerConfig,
    CircuitBreakerPlugin,
    CircuitState,
    PlaneHealth,
    get_fallbacks,
    register_fallback,
)
from .health import HealthMonitor
from .recovery import Checkpoint, RecoveryEngine, RecoveryResult

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
