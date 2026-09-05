"""Tests for the Rollback Infrastructure Plugin — canary/freeze/rollback (v7 §112).

Covers: SystemVersion, CanaryDeployment, DriftAlert, RollbackEngine, RollbackPlugin
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from plugins.rollback import (
    CanaryDeployment,
    DriftAlert,
    RollbackEngine,
    RollbackPlugin,
    SystemVersion,
)
from plugins.rollback import (
    create as create_rollback,
)


class TestSystemVersion:
    """Tests for SystemVersion dataclass."""

    def test_create_version(self):
        v = SystemVersion(version_id="v1", parent=None, components={"plugin": "1.0.0"})
        assert v.version_id == "v1"
        assert v.parent is None
        assert v.components == {"plugin": "1.0.0"}
        assert v.promoted is False
        assert v.rolled_back is False

    def test_create_with_parent(self):
        v = SystemVersion(version_id="v2", parent="v1", components={})
        assert v.parent == "v1"


class TestCanaryDeployment:
    """Tests for CanaryDeployment dataclass."""

    def test_create_canary(self):
        c = CanaryDeployment(id="c1", version="v1", stage="5%", status="running")
        assert c.id == "c1"
        assert c.stage == "5%"
        assert c.status == "running"


class TestDriftAlert:
    """Tests for DriftAlert dataclass."""

    def test_create_alert(self):
        a = DriftAlert(id="a1", metric="latency", baseline=100.0, current=150.0, drift_pct=0.5)
        assert a.metric == "latency"
        assert a.baseline == 100.0
        assert a.current == 150.0
        assert a.drift_pct == 0.5


class TestRollbackEngine:
    """Tests for the RollbackEngine."""

    def test_create_version(self):
        engine = RollbackEngine()
        v = engine.create_version({"plugin": "1.0.0"})
        assert v.version_id is not None
        assert v.parent is None
        assert len(engine._versions) == 1

    def test_create_version_with_parent(self):
        engine = RollbackEngine()
        v1 = engine.create_version({"p": "1.0"})
        engine.promote_version(v1.version_id)
        v2 = engine.create_version({"p": "2.0"})
        assert v2.parent == v1.version_id

    def test_promote_version(self):
        engine = RollbackEngine()
        v = engine.create_version({"p": "1.0"})
        assert engine.promote_version(v.version_id) is True
        assert engine._current_version == v.version_id
        assert v.promoted is True

    def test_promote_nonexistent(self):
        engine = RollbackEngine()
        assert engine.promote_version("nonexistent") is False

    def test_rollback(self):
        engine = RollbackEngine()
        v1 = engine.create_version({"p": "1.0"})
        engine.promote_version(v1.version_id)
        v2 = engine.create_version({"p": "2.0"})
        engine.promote_version(v2.version_id)
        
        result = engine.rollback()
        assert result == v1.version_id
        assert engine._current_version == v1.version_id
        assert v2.rolled_back is True

    def test_rollback_no_parent(self):
        engine = RollbackEngine()
        v = engine.create_version({"p": "1.0"})
        engine.promote_version(v.version_id)
        result = engine.rollback()
        assert result is None

    def test_rollback_no_current(self):
        engine = RollbackEngine()
        result = engine.rollback()
        assert result is None

    def test_start_canary(self):
        engine = RollbackEngine()
        v = engine.create_version({"p": "1.0"})
        canary = engine.start_canary(v.version_id)
        assert canary.version == v.version_id
        assert canary.stage == "5%"
        assert canary.status == "running"

    def test_advance_canary(self):
        engine = RollbackEngine()
        v = engine.create_version({"p": "1.0"})
        canary = engine.start_canary(v.version_id)
        assert engine.advance_canary(canary.id) is True
        assert canary.stage == "25%"

    def test_advance_canary_to_completion(self):
        engine = RollbackEngine()
        v = engine.create_version({"p": "1.0"})
        canary = engine.start_canary(v.version_id)
        engine.advance_canary(canary.id)  # 25%
        engine.advance_canary(canary.id)  # 50%
        engine.advance_canary(canary.id)  # 100%
        assert canary.stage == "100%"
        assert canary.status == "passed"
        assert engine._current_version == v.version_id

    def test_advance_nonexistent_canary(self):
        engine = RollbackEngine()
        assert engine.advance_canary("nonexistent") is False

    def test_advance_frozen_canary(self):
        engine = RollbackEngine()
        v = engine.create_version({"p": "1.0"})
        canary = engine.start_canary(v.version_id)
        canary.status = "frozen"
        assert engine.advance_canary(canary.id) is False

    def test_detect_drift(self):
        engine = RollbackEngine()
        alert = engine.detect_drift("latency", baseline=100.0, current=150.0, threshold=0.1)
        assert alert is not None
        assert alert.metric == "latency"
        assert alert.drift_pct == pytest.approx(0.5)

    def test_detect_drift_below_threshold(self):
        engine = RollbackEngine()
        alert = engine.detect_drift("latency", baseline=100.0, current=105.0, threshold=0.1)
        assert alert is None

    def test_detect_drift_zero_baseline(self):
        engine = RollbackEngine()
        alert = engine.detect_drift("metric", baseline=0.0, current=100.0)
        assert alert is None

    def test_get_current_version(self):
        engine = RollbackEngine()
        v = engine.create_version({"p": "1.0"})
        engine.promote_version(v.version_id)
        current = engine.get_current_version()
        assert current is not None
        assert current.version_id == v.version_id

    def test_get_current_version_none(self):
        engine = RollbackEngine()
        assert engine.get_current_version() is None

    def test_get_version_history(self):
        engine = RollbackEngine()
        engine.create_version({"p": "1.0"})
        engine.create_version({"p": "2.0"})
        history = engine.get_version_history()
        assert len(history) == 2

    def test_get_stats(self):
        engine = RollbackEngine()
        engine.create_version({"p": "1.0"})
        stats = engine.get_stats()
        assert stats["total_versions"] == 1
        assert stats["canaries"] == 0
        assert stats["drift_alerts"] == 0

    def test_canary_stages_progression(self):
        engine = RollbackEngine()
        v = engine.create_version({"p": "1.0"})
        canary = engine.start_canary(v.version_id)
        
        stages_seen = [canary.stage]
        while canary.stage != "100%" and canary.status == "running":
            engine.advance_canary(canary.id)
            stages_seen.append(canary.stage)
        
        assert stages_seen == ["5%", "25%", "50%", "100%"]

    def test_multiple_rollbacks(self):
        engine = RollbackEngine()
        v1 = engine.create_version({"p": "1.0"})
        engine.promote_version(v1.version_id)
        v2 = engine.create_version({"p": "2.0"})
        engine.promote_version(v2.version_id)
        v3 = engine.create_version({"p": "3.0"})
        engine.promote_version(v3.version_id)
        
        engine.rollback()  # back to v2
        assert engine._current_version == v2.version_id
        engine.rollback()  # back to v1
        assert engine._current_version == v1.version_id


class TestRollbackPlugin:
    """Tests for the RollbackPlugin wrapper."""

    @pytest.mark.asyncio
    async def test_create(self):
        plugin = RollbackPlugin()
        assert plugin.engine is not None

    @pytest.mark.asyncio
    async def test_create_with_kernel(self):
        plugin = await create_rollback(kernel="fake_kernel")
        assert plugin._kernel == "fake_kernel"

    @pytest.mark.asyncio
    async def test_load(self):
        plugin = RollbackPlugin()
        await plugin.load()

    @pytest.mark.asyncio
    async def test_start_stop(self):
        plugin = RollbackPlugin()
        await plugin.start()
        await plugin.stop()

    @pytest.mark.asyncio
    async def test_health(self):
        plugin = RollbackPlugin()
        h = await plugin.health()
        assert h["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_create_version(self):
        plugin = RollbackPlugin()
        v = await plugin.create_version({"p": "1.0"})
        assert v.version_id is not None

    @pytest.mark.asyncio
    async def test_rollback(self):
        plugin = RollbackPlugin()
        v1 = await plugin.create_version({"p": "1.0"})
        plugin.engine.promote_version(v1.version_id)
        v2 = await plugin.create_version({"p": "2.0"})
        plugin.engine.promote_version(v2.version_id)
        result = await plugin.rollback()
        assert result == v1.version_id


class TestRollbackIntegration:
    """Integration tests for rollback infrastructure."""

    def test_full_canary_lifecycle(self):
        engine = RollbackEngine()
        
        # Create and promote initial version
        v1 = engine.create_version({"p": "1.0"})
        engine.promote_version(v1.version_id)
        
        # Start canary for new version
        v2 = engine.create_version({"p": "2.0"})
        canary = engine.start_canary(v2.version_id)
        
        # Advance through stages
        for _ in range(3):
            engine.advance_canary(canary.id)
        
        assert canary.status == "passed"
        assert engine._current_version == v2.version_id

    def test_drift_triggers_rollback(self):
        engine = RollbackEngine()
        
        v1 = engine.create_version({"p": "1.0"})
        engine.promote_version(v1.version_id)
        v2 = engine.create_version({"p": "2.0"})
        engine.promote_version(v2.version_id)
        
        # Detect drift
        alert = engine.detect_drift("error_rate", baseline=0.01, current=0.15, threshold=0.1)
        assert alert is not None
        
        # Rollback due to drift
        result = engine.rollback()
        assert result == v1.version_id

    def test_version_lineage(self):
        engine = RollbackEngine()
        
        v1 = engine.create_version({"p": "1.0"})
        engine.promote_version(v1.version_id)
        v2 = engine.create_version({"p": "2.0"})
        engine.promote_version(v2.version_id)
        v3 = engine.create_version({"p": "3.0"})
        
        # Check lineage
        assert v2.parent == v1.version_id
        assert v3.parent == v2.version_id

    def test_drift_alerts_accumulate(self):
        engine = RollbackEngine()
        
        engine.detect_drift("latency", 100, 150, 0.1)
        engine.detect_drift("error_rate", 0.01, 0.05, 0.1)
        engine.detect_drift("throughput", 1000, 500, 0.1)
        
        assert len(engine._drift_alerts) == 3
