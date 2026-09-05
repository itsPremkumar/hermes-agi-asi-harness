"""Tests for the Scenario Harness Plugin — structured evaluation (v7 §45).

Covers: Scenario, ScenarioResult, ScenarioHarness, ScenarioHarnessPlugin
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from plugins.scenario_harness import (
    Scenario,
    ScenarioHarness,
    ScenarioHarnessPlugin,
    ScenarioResult,
)
from plugins.scenario_harness import (
    create as create_scenario_harness,
)


class TestScenario:
    """Tests for Scenario dataclass."""

    def test_create_scenario(self):
        s = Scenario(id="test-001", category="nominal", name="Test", description="A test")
        assert s.id == "test-001"
        assert s.category == "nominal"
        assert s.split == "dev"
        assert s.difficulty == 0.5

    def test_create_with_custom_split(self):
        s = Scenario(id="t1", category="adversarial", name="Adv", description="Adversarial test", split="redteam")
        assert s.split == "redteam"

    def test_create_with_expected_outcome(self):
        s = Scenario(
            id="t2", category="nominal", name="Math", description="Compute",
            expected_outcome={"result": 42}
        )
        assert s.expected_outcome == {"result": 42}


class TestScenarioResult:
    """Tests for ScenarioResult dataclass."""

    def test_create_result(self):
        r = ScenarioResult(scenario_id="s1", passed=True, score=0.95)
        assert r.scenario_id == "s1"
        assert r.passed is True
        assert r.score == 0.95

    def test_create_failed_result(self):
        r = ScenarioResult(scenario_id="s2", passed=False, score=0.2)
        assert r.passed is False


class TestScenarioHarness:
    """Tests for the ScenarioHarness engine."""

    def test_default_scenarios_loaded(self):
        harness = ScenarioHarness()
        assert len(harness._scenarios) >= 12

    def test_get_scenario(self):
        harness = ScenarioHarness()
        s = harness._scenarios.get("nom-001")
        assert s is not None
        assert s.category == "nominal"

    def test_get_scenarios_by_category(self):
        harness = ScenarioHarness()
        nominal = harness.get_scenarios(category="nominal")
        assert len(nominal) >= 1

    def test_get_scenarios_by_split(self):
        harness = ScenarioHarness()
        redteam = harness.get_scenarios(split="redteam")
        assert len(redteam) >= 1

    def test_get_categories(self):
        harness = ScenarioHarness()
        cats = harness.get_categories()
        assert isinstance(cats, list)
        assert "nominal" in cats

    def test_get_evaluation_splits(self):
        harness = ScenarioHarness()
        splits = harness.get_evaluation_splits()
        assert "dev" in splits

    def test_register_custom_scenario(self):
        harness = ScenarioHarness()
        custom = Scenario(id="custom-001", category="custom", name="Custom", description="Custom scenario")
        harness.register_scenario(custom)
        assert "custom-001" in harness._scenarios

    def test_get_stats(self):
        harness = ScenarioHarness()
        stats = harness.get_stats()
        assert "total_scenarios" in stats
        assert "categories" in stats
        assert "splits" in stats
        assert stats["total_scenarios"] >= 12

    @pytest.mark.asyncio
    async def test_run_scenario_not_found(self):
        harness = ScenarioHarness()
        result = await harness.run_scenario("nonexistent")
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_run_scenario(self):
        harness = ScenarioHarness()
        result = await harness.run_scenario("nom-001")
        assert isinstance(result, ScenarioResult)
        assert result.scenario_id == "nom-001"

    @pytest.mark.asyncio
    async def test_run_suite(self):
        harness = ScenarioHarness()
        result = await harness.run_suite()
        assert "passed" in result
        assert "total" in result
        assert "avg_score" in result
        assert result["total"] >= 12

    @pytest.mark.asyncio
    async def test_run_suite_by_category(self):
        harness = ScenarioHarness()
        result = await harness.run_suite(category="nominal")
        assert "total" in result

    @pytest.mark.asyncio
    async def test_run_suite_by_split(self):
        harness = ScenarioHarness()
        result = await harness.run_suite(split="redteam")
        assert "total" in result


class TestScenarioHarnessPlugin:
    """Tests for the ScenarioHarnessPlugin wrapper."""

    @pytest.mark.asyncio
    async def test_create(self):
        plugin = ScenarioHarnessPlugin()
        assert plugin.harness is not None

    @pytest.mark.asyncio
    async def test_create_with_kernel(self):
        plugin = await create_scenario_harness(kernel="fake_kernel")
        assert plugin._kernel == "fake_kernel"

    @pytest.mark.asyncio
    async def test_load(self):
        plugin = ScenarioHarnessPlugin()
        await plugin.load()

    @pytest.mark.asyncio
    async def test_start_stop(self):
        plugin = ScenarioHarnessPlugin()
        await plugin.start()
        await plugin.stop()

    @pytest.mark.asyncio
    async def test_health(self):
        plugin = ScenarioHarnessPlugin()
        h = await plugin.health()
        assert h["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_run_suite(self):
        plugin = ScenarioHarnessPlugin()
        result = await plugin.run_suite()
        assert "total" in result
        assert result["total"] >= 12


class TestScenarioIntegration:
    """Integration tests for scenario harness."""

    @pytest.mark.asyncio
    async def test_full_evaluation_cycle(self):
        harness = ScenarioHarness()
        result = await harness.run_suite()
        
        assert result["total"] >= 12
        assert "passed" in result
        assert "avg_score" in result
        assert 0.0 <= result["avg_score"] <= 1.0

    def test_scenario_categories_coverage(self):
        harness = ScenarioHarness()
        cats = harness.get_categories()
        assert "nominal" in cats
        assert "adversarial" in cats
        assert "safety_critical" in cats

    def test_scenario_splits_coverage(self):
        harness = ScenarioHarness()
        splits = harness.get_evaluation_splits()
        assert "dev" in splits
        assert "redteam" in splits
        assert "novel" in splits

    def test_redteam_scenarios_exist(self):
        harness = ScenarioHarness()
        redteam = harness.get_scenarios(split="redteam")
        assert len(redteam) >= 1

    def test_novel_scenarios_exist(self):
        harness = ScenarioHarness()
        novel = harness.get_scenarios(split="novel")
        assert len(novel) >= 1
