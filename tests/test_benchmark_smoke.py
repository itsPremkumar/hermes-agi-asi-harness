"""Regression tests: benchmark execution must be real, never fabricated.

Covers the wakeup-21 fix where `hermes_agi benchmark` returned
13x not_implemented (wrong script filenames) while the mock plugin
returned a hardcoded score of 0.85.
"""

from __future__ import annotations

import pytest

from hermes_agi.benchmarks import BENCHMARK_REGISTRY
from hermes_agi.plugins.core_plugins import BenchmarkPlugin
from hermes_agi.plugins.real_plugins import RealBenchmarkPlugin


@pytest.mark.parametrize("name", sorted(BENCHMARK_REGISTRY))
async def test_real_benchmark_smoke_passes_offline(name: str):
    """Every registered benchmark imports, instantiates, and probes offline."""
    plugin = RealBenchmarkPlugin()
    result = await plugin._execute_benchmark(name)
    assert result["status"] == "smoke_passed", result
    assert result["class"].endswith("Benchmark")
    assert result["module"].endswith(".py")
    assert isinstance(result["facts"], dict) and result["facts"], result
    assert result["duration_s"] >= 0
    # Full scoring needs data + model: reported as not-run, never a number.
    assert "scoring" in result
    assert "score" not in result and "accuracy" not in result


async def test_real_benchmark_unknown_name_is_honest():
    plugin = RealBenchmarkPlugin()
    result = await plugin._execute_benchmark("no_such_bench")
    assert result.get("error") == "Unknown benchmark: no_such_bench"
    assert "score" not in result


async def test_real_benchmark_all_has_no_fake_scores():
    plugin = RealBenchmarkPlugin()
    result = await plugin._run_benchmark(name="all")
    assert set(result["benchmarks"]) == set(BENCHMARK_REGISTRY)
    for bench_result in result["benchmarks"].values():
        assert bench_result["status"] == "smoke_passed", bench_result
        assert "score" not in bench_result


async def test_mock_benchmark_never_fabricates_score():
    """Mock-mode plugin must not return the old hardcoded 0.85."""
    plugin = BenchmarkPlugin()
    single = await plugin._run_benchmark(name="mmlu")
    assert single["status"] == "mock"
    assert single["score"] is None
    all_result = await plugin._run_benchmark(name="all")
    for bench_result in all_result["benchmarks"].values():
        assert bench_result["status"] == "mock"
        assert bench_result["score"] is None
