"""Tests for production_hardened layer."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.production.production_hardened import (
    ProductionHardenedLayer,
    GracefulDegradationManager,
    CanaryDeploymentManager,
    DriftDetector,
    AutoRollbackManager,
    SafetyRollbackTrigger,
    RollbackReason,
    DeploymentVersion,
)


async def test_full_layer():
    layer = ProductionHardenedLayer()
    await layer.initialize({})

    # 1. Graceful degradation
    layer.degradation.register_feature("search", enabled=True)
    layer.degradation.register_feature("research", enabled=False)
    assert layer.degradation.is_enabled("search") is True
    assert layer.degradation.is_enabled("research") is False

    async def primary_search():
        return {"results": ["doc1", "doc2"]}

    async def fallback_search():
        return {"results": [], "fallback": True}

    layer.degradation.register_fallback("search", fallback_search)
    result, used_fb = await layer.degradation.execute("search", primary_search)
    assert result == {"results": ["doc1", "doc2"]}
    assert used_fb is False

    # Disabled feature uses fallback
    result, used_fb = await layer.degradation.execute("research", primary_search)
    assert used_fb is True

    # 2. Canary deployment
    layer.canary.register_version("v1.0", "abc123", weight=0.9)
    layer.canary.register_version("v1.1", "def456", weight=0.1)
    status = layer.canary.get_status()
    assert "v1.0" in status["versions"]
    assert "v1.1" in status["versions"]

    # Record predictions
    for i in range(60):
        layer.canary.record_prediction("v1.1", 0.9, 0.91, safety_score=0.95)

    result = layer.canary.evaluate_canary("v1.1")
    assert result.promoted is True
    assert result.safety_score == 0.95

    # 3. Drift detection
    layer.drift.set_baseline("v1.0", mean=0.5, std=0.05)
    for i in range(30):
        layer.drift.record("v1.0", 0.5 + (i * 0.02), 0.5)

    report = layer.drift.get_drift_report()
    assert "v1.0" in report["drift_scores"]

    # 4. Auto-rollback
    layer.rollback.register_safety_hook(lambda: True)
    hook_result = layer.rollback.check_safety_hooks()
    assert hook_result is not None

    # 5. Execute with protection (no safety hook trigger)
    async def op():
        return 42.0

    result, used_fb, meta = await layer.execute_with_protection("test", "v1.0", op)
    # Safety hook returns True → rollback → result is None
    assert meta["rollback_triggered"] is True

    # 6. Dashboard
    dashboard = layer.get_dashboard()
    assert "degradation" in dashboard
    assert "canary" in dashboard
    assert "drift" in dashboard
    assert "rollback" in dashboard
    assert "safety_trigger_violations" in dashboard

    print("✅ All production_hardened tests passed!")
    print(f"   Dashboard: {json.dumps(dashboard, indent=2, default=str)[:500]}")


import json

if __name__ == "__main__":
    asyncio.run(test_full_layer())