"""Circuit breaker smoke test."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from hermes.plugins.circuit_breaker import (
    CircuitBreakerPlugin,
    CircuitBreakerConfig,
    HealthMonitor,
    RecoveryEngine,
    CircuitState,
)


async def test_circuit_breaker():
    cb = CircuitBreakerPlugin()
    cb.configure_plane("meta_reasoning", CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=5.0,
        success_threshold=2,
        timeout=2.0,
        max_retries=2,
        backoff_base=0.1,
        backoff_max=1.0,
    ))

    monitor = HealthMonitor(cb)
    recovery = RecoveryEngine(cb)

    # Simulate successful calls
    async def success_op():
        return {"result": "ok"}

    result, used_fallback = await cb.call_plane("meta_reasoning", success_op)
    assert result == {"result": "ok"}
    assert used_fallback is False

    # Simulate failing calls
    async def failing_op():
        raise RuntimeError("Plane failure")

    result, used_fallback = await cb.call_plane("meta_reasoning", failing_op)
    assert result is None
    assert used_fallback is False

    # Check health
    health = monitor.get_plane_health("meta_reasoning")
    assert health["total_calls"] == 4  # 1 success + 3 failures (1 initial + 2 retries)
    assert health["failed_calls"] >= 2

    # Check system health
    system = monitor.get_system_health()
    assert system["planes"] == 1

    # Test recovery with fallback
    async def fallback_fn():
        return {"result": "from_fallback"}

    result, used_fallback = await cb.call_plane("meta_reasoning", failing_op, fallback=fallback_fn)
    assert result == {"result": "from_fallback"}
    assert used_fallback is True

    # Test checkpoint
    recovery.save_checkpoint("task_1", "meta_reasoning", {"step": 3}, completed_planes=["research"])
    cp = recovery.load_checkpoint("task_1")
    assert cp is not None
    assert cp.state["step"] == 3

    # Test escalation
    esc = recovery.escalate("meta_reasoning", "Critical failure", severity="critical")
    assert esc["action_required"] is True
    assert "Disable" in esc["recommended_action"] or "fallback" in esc["recommended_action"]

    print("✅ All circuit breaker tests passed!")
    print(f"   System health: {monitor.get_system_health()}")


if __name__ == "__main__":
    asyncio.run(test_circuit_breaker())
