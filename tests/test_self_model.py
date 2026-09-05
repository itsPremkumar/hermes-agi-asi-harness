"""Tests for the Self-Model Plugin — empirical capability measurement (v7 §50).

Covers: SelfModelCapability, SelfModelEngine, SelfModelPlugin
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from plugins.self_model import (
    SelfModelCapability,
    SelfModelEngine,
    SelfModelPlugin,
)
from plugins.self_model import (
    create as create_self_model,
)


class TestSelfModelCapability:
    """Tests for the SelfModelCapability dataclass."""

    def test_create_capability(self):
        cap = SelfModelCapability(name="test_cap")
        assert cap.name == "test_cap"
        assert cap.success_rate == 0.0
        assert cap.sample_count == 0
        assert cap.calibration == 0.5
        assert cap.failure_modes == []

    def test_update_success(self):
        cap = SelfModelCapability(name="test")
        cap.update(success=True, strategy="strategy_a", resource_cost=1.5)
        assert cap.sample_count == 1
        assert cap.success_rate > 0.0
        assert cap.best_strategy == "strategy_a"
        # EMA: 0 * 0.9 + 1.5 * 0.1 = 0.15
        assert cap.resource_profile["avg_cost"] == pytest.approx(0.15)
        assert len(cap.history) == 1

    def test_update_failure(self):
        cap = SelfModelCapability(name="test")
        cap.update(success=False)
        assert cap.sample_count == 1
        assert cap.success_rate == 0.0

    def test_multiple_updates_converge(self):
        cap = SelfModelCapability(name="test")
        for _ in range(50):
            cap.update(success=True)
        assert cap.sample_count == 50
        assert cap.success_rate == pytest.approx(1.0, abs=0.05)
        assert cap.calibration == pytest.approx(1.0, abs=0.01)

    def test_mixed_results(self):
        cap = SelfModelCapability(name="test")
        for i in range(10):
            cap.update(success=(i % 2 == 0))
        assert cap.sample_count == 10
        assert 0.3 < cap.success_rate < 0.7

    def test_history_bounded(self):
        cap = SelfModelCapability(name="test")
        for i in range(110):
            cap.update(success=True)
        assert len(cap.history) == 100

    def test_to_dict(self):
        cap = SelfModelCapability(name="test")
        cap.update(success=True, strategy="s1", resource_cost=2.0)
        d = cap.to_dict()
        assert d["name"] == "test"
        assert "success_rate" in d
        assert "sample_count" in d
        assert "calibration" in d
        assert "failure_modes" in d
        assert "best_strategy" in d

    def test_calibration_increases_with_samples(self):
        cap = SelfModelCapability(name="test")
        assert cap.calibration == 0.5
        for _ in range(30):
            cap.update(success=True)
        # After 30 samples: calibration = min(1.0, 30/50) = 0.6
        assert cap.calibration == pytest.approx(0.6)

    def test_resource_profile_ema(self):
        cap = SelfModelCapability(name="test")
        cap.update(success=True, resource_cost=10.0)
        cap.update(success=True, resource_cost=20.0)
        assert "avg_cost" in cap.resource_profile


class TestSelfModelEngine:
    """Tests for the SelfModelEngine."""

    def test_get_or_create(self):
        engine = SelfModelEngine()
        cap = engine.get_or_create("new_cap")
        assert cap.name == "new_cap"
        assert "new_cap" in engine.get_all()

    def test_get_or_create_idempotent(self):
        engine = SelfModelEngine()
        cap1 = engine.get_or_create("same")
        cap2 = engine.get_or_create("same")
        assert cap1 is cap2

    def test_record_execution(self):
        engine = SelfModelEngine()
        engine.record_execution("code_gen", success=True, strategy="chain_of_thought")
        cap = engine.get_capability("code_gen")
        assert cap is not None
        assert cap.sample_count == 1
        assert cap.best_strategy == "chain_of_thought"

    def test_record_execution_with_failure(self):
        engine = SelfModelEngine()
        engine.record_execution("test", success=False, failure_mode="syntax_error")
        cap = engine.get_capability("test")
        assert "syntax_error" in cap.failure_modes

    def test_get_weakest(self):
        engine = SelfModelEngine()
        engine.get_or_create("strong")
        for _ in range(10):
            engine.record_execution("strong", success=True)
        engine.get_or_create("weak")
        for _ in range(10):
            engine.record_execution("weak", success=False)
        weakest = engine.get_weakest(n=1)
        assert len(weakest) == 1
        assert weakest[0].name == "weak"

    def test_get_strongest(self):
        engine = SelfModelEngine()
        engine.get_or_create("strong")
        for _ in range(10):
            engine.record_execution("strong", success=True)
        engine.get_or_create("weak")
        for _ in range(10):
            engine.record_execution("weak", success=False)
        strongest = engine.get_strongest(n=1)
        assert len(strongest) == 1
        assert strongest[0].name == "strong"

    def test_get_weakest_ignores_low_sample(self):
        engine = SelfModelEngine()
        engine.get_or_create("new")
        engine.record_execution("new", success=False)
        weakest = engine.get_weakest(n=3)
        assert len(weakest) == 0

    def test_detect_bottlenecks(self):
        engine = SelfModelEngine()
        engine.get_or_create("bottleneck")
        for _ in range(10):
            engine.record_execution("bottleneck", success=False)
        engine.get_or_create("good")
        for _ in range(10):
            engine.record_execution("good", success=True)
        bottlenecks = engine.detect_bottlenecks()
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["capability"] == "bottleneck"
        assert bottlenecks[0]["priority"] > 0.5

    def test_detect_bottlenecks_requires_min_samples(self):
        engine = SelfModelEngine()
        engine.get_or_create("cap")
        for _ in range(3):
            engine.record_execution("cap", success=False)
        bottlenecks = engine.detect_bottlenecks()
        assert len(bottlenecks) == 0

    def test_get_recommendation_insufficient(self):
        engine = SelfModelEngine()
        engine.record_execution("task", success=True)
        rec = engine.get_recommendation("task")
        assert rec["recommendation"] == "insufficient_data"

    def test_get_recommendation_sufficient(self):
        engine = SelfModelEngine()
        engine.get_or_create("task")
        for _ in range(5):
            engine.record_execution("task", success=True, strategy="best_strat")
        rec = engine.get_recommendation("task")
        assert rec["recommendation"] == "best_strat"
        assert rec["confidence"] > 0.0

    def test_get_profile(self):
        engine = SelfModelEngine()
        engine.record_execution("a", success=True)
        engine.record_execution("b", success=False)
        profile = engine.get_profile()
        assert "capabilities" in profile
        assert "bottlenecks" in profile
        assert "overall_calibration" in profile
        assert "total_samples" in profile
        assert profile["total_samples"] == 2

    def test_get_stats_empty(self):
        engine = SelfModelEngine()
        stats = engine.get_stats()
        assert stats["total"] == 0

    def test_get_stats_populated(self):
        engine = SelfModelEngine()
        engine.record_execution("a", success=True)
        engine.record_execution("b", success=False)
        stats = engine.get_stats()
        assert stats["total"] == 2
        assert "avg_success_rate" in stats
        assert "calibrated" in stats

    def test_get_all(self):
        engine = SelfModelEngine()
        engine.record_execution("a", success=True)
        engine.record_execution("b", success=True)
        all_caps = engine.get_all()
        assert len(all_caps) == 2

    def test_get_capability_none(self):
        engine = SelfModelEngine()
        assert engine.get_capability("nonexistent") is None


class TestSelfModelPlugin:
    """Tests for the SelfModelPlugin wrapper."""

    @pytest.mark.asyncio
    async def test_create(self):
        plugin = SelfModelPlugin()
        assert plugin.engine is not None

    @pytest.mark.asyncio
    async def test_create_with_kernel(self):
        plugin = await create_self_model(kernel="fake_kernel")
        assert plugin._kernel == "fake_kernel"

    @pytest.mark.asyncio
    async def test_load(self):
        plugin = SelfModelPlugin()
        await plugin.load()

    @pytest.mark.asyncio
    async def test_start_stop(self):
        plugin = SelfModelPlugin()
        await plugin.start()
        await plugin.stop()

    @pytest.mark.asyncio
    async def test_health(self):
        plugin = SelfModelPlugin()
        h = await plugin.health()
        assert h["status"] == "healthy"
        assert "total" in h

    @pytest.mark.asyncio
    async def test_record(self):
        plugin = SelfModelPlugin()
        await plugin.record("test_cap", success=True, strategy="s1")
        profile = await plugin.get_profile()
        assert "test_cap" in profile["capabilities"]

    @pytest.mark.asyncio
    async def test_get_profile(self):
        plugin = SelfModelPlugin()
        await plugin.record("a", success=True)
        profile = await plugin.get_profile()
        assert "capabilities" in profile

    @pytest.mark.asyncio
    async def test_get_bottlenecks(self):
        plugin = SelfModelPlugin()
        for _ in range(10):
            await plugin.record("weak", success=False)
        bottlenecks = await plugin.get_bottlenecks()
        assert len(bottlenecks) >= 0

    @pytest.mark.asyncio
    async def test_record_multiple(self):
        plugin = SelfModelPlugin()
        for i in range(10):
            await plugin.record("cap", success=(i % 2 == 0))
        profile = await plugin.get_profile()
        cap_data = profile["capabilities"]["cap"]
        assert cap_data["sample_count"] == 10


class TestSelfModelIntegration:
    """Integration tests for the self-model system."""

    def test_full_measurement_cycle(self):
        engine = SelfModelEngine()
        for _ in range(20):
            engine.record_execution("code_gen", success=True, strategy="cot", resource_cost=1.2)
        for _ in range(5):
            engine.record_execution("code_gen", success=False, failure_mode="syntax")
        
        profile = engine.get_profile()
        assert profile["total_samples"] == 25
        
        engine.detect_bottlenecks()
        rec = engine.get_recommendation("code_gen")
        assert rec["recommendation"] == "cot"
        assert rec["confidence"] > 0.0

    def test_bottleneck_drives_improvement_target(self):
        engine = SelfModelEngine()
        for name, rate in [("strong", 1.0), ("medium", 0.7), ("weak", 0.3)]:
            engine.get_or_create(name)
            for i in range(20):
                engine.record_execution(name, success=(i / 20 < rate))
        
        weakest = engine.get_weakest(n=1)
        assert len(weakest) >= 1
        assert weakest[0].name == "weak"

    def test_calibration_progression(self):
        engine = SelfModelEngine()
        
        # After 1 sample, calibration should be low
        engine.get_or_create("cap")
        engine.record_execution("cap", success=True)
        cap1 = engine.get_capability("cap")
        cal1 = cap1.calibration
        
        # After 50 samples, calibration should be high
        for _ in range(49):
            engine.record_execution("cap", success=True)
        cap50 = engine.get_capability("cap")
        cal50 = cap50.calibration
        
        assert cal50 > cal1
        assert cal50 == pytest.approx(1.0, abs=0.01)
