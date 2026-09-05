"""
Phase 6 Test Suite — Evolution

Tests:
1. Evolution Safety Loop: submit mod, run safety checks, approve/reject
2. Benchmark DB: record runs, trends, regression detection, leaderboard
3. Self-Improvement Boundary: change level rules, can_change, log
4. World Sync: ingest changes, relevance filtering, opportunities, stats
5. E2E: all Phase 6 plugins in kernel
"""

import os

os.environ.setdefault("HERMES_HOME", "/tmp/hermes_phase6_test")

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def header(text):
    print(f"\n{'='*70}\n  {text}\n{'='*70}")


def _pass(name):
    print(f"  ✓ {name}")


def _fail(name, err):
    print(f"  ✗ {name}: {err}")




async def test_1_evolution_safety_loop():
    """Test 1: Evolution Safety Loop."""
    header("Test 1: Evolution Safety Loop")

    from plugins.evolution_safety_loop import (
        ModificationType,
    )
    from plugins.evolution_safety_loop import (
        create as esl_create,
    )
    plugin = await esl_create()
    await plugin.load()

    # Submit a SAFE modification
    safe = plugin.engine.submit_modification(
        mod_type=ModificationType.PROCEDURE.value,
        description="Optimize file read workflow",
        blast_radius=2,
        reversibility=0.95,
        value_alignment_score=0.95,
        test_coverage=0.85,
        rollback_plan="Restore previous workflow from version control",
    )
    assert safe.approved, f"Safe mod should be approved: {safe.rejection_reason}"
    _pass(f"Safe modification approved: {safe.modification_id}")

    # Submit a HIGH-RISK modification (should be rejected)
    risky = plugin.engine.submit_modification(
        mod_type=ModificationType.POLICY.value,
        description="Modify authority hierarchy",
        blast_radius=8,  # over limit
        reversibility=0.5,  # below threshold
        value_alignment_score=0.6,  # below threshold
        test_coverage=0.4,  # below threshold
        rollback_plan="",  # empty
    )
    assert risky.rejected, f"Risky mod should be rejected: {risky.to_dict()}"
    _pass(f"Risky modification rejected: {risky.rejection_reason}")

    # Submit a FORBIDDEN modification
    forbidden = plugin.engine.submit_modification(
        mod_type=ModificationType.CONSTITUTION.value,
        description="Modify core identity",
        blast_radius=1,
        reversibility=0.99,
        value_alignment_score=1.0,
        test_coverage=1.0,
        rollback_plan="restore",
    )
    assert forbidden.rejected, "Constitution changes must be forbidden"
    _pass(f"Constitution change rejected: {forbidden.rejection_reason}")

    # Stats
    stats = plugin.engine.get_stats()
    _pass(f"Stats: {stats}")



async def test_2_benchmark_db():
    """Test 2: Benchmark DB."""
    header("Test 2: Benchmark DB")

    from plugins.benchmark_db import create as bdb_create
    plugin = await bdb_create()
    await plugin.load()

    # Record runs
    for score in [0.6, 0.65, 0.7, 0.72, 0.75, 0.5, 0.4]:
        plugin.engine.record_run(
            benchmark_name="reasoning_v1",
            score=score,
            duration_seconds=2.0,
        )
    _pass("Recorded 7 runs")

    # Get trend
    trend = plugin.engine.get_trend("reasoning_v1", limit=5)
    assert len(trend) == 5
    _pass(f"Recent trend: {[f'{s:.2f}' for s in trend]}")

    # Detect regression
    regression = plugin.engine.detect_regression("reasoning_v1", threshold=0.1)
    assert regression is not None
    assert regression["regression_detected"]
    _pass(f"Regression detected: recent={regression['recent_avg']:.2f}, baseline={regression['baseline_avg']:.2f}")

    # Leaderboard
    lb = plugin.engine.get_leaderboard()
    assert len(lb) >= 1
    _pass(f"Leaderboard: {lb[0]['benchmark']} = {lb[0]['best_score']:.2f}")

    # Stats
    stats = plugin.engine.get_stats()
    _pass(f"Stats: {stats}")



async def test_3_self_improvement_boundary():
    """Test 3: Self-Improvement Boundary."""
    header("Test 3: Self-Improvement Boundary")

    from plugins.self_improvement_boundary import (
        ChangeLevel,
    )
    from plugins.self_improvement_boundary import (
        create as sib_create,
    )
    plugin = await sib_create()
    await plugin.load()

    # Test can_change
    assert plugin.engine.can_change("workflow_procedure")
    _pass("Can change workflow_procedure autonomously")

    assert not plugin.engine.can_change("constitution")
    _pass("Cannot change constitution (forbidden)")

    assert not plugin.engine.can_change("shutdown_mechanisms")
    _pass("Cannot change shutdown_mechanisms (forbidden)")

    # Required level
    level = plugin.engine.get_required_level("model_selection")
    assert level == ChangeLevel.APPROVED
    _pass(f"model_selection requires: {level.value}")

    # Log change
    plugin.engine.log_change("workflow_procedure", ChangeLevel.AUTONOMOUS,
                             "Optimized file read")
    log = plugin.engine.get_change_log()
    assert len(log) == 1
    _pass(f"Change logged: {log[0]['target']}")

    # Stats
    stats = plugin.engine.get_stats()
    _pass(f"Stats: {stats}")



async def test_4_world_sync():
    """Test 4: World Sync."""
    header("Test 4: World Sync")

    from plugins.world_sync import SyncSource
    from plugins.world_sync import create as ws_create
    plugin = await ws_create()
    await plugin.load()

    # Ingest changes
    plugin.engine.ingest_change(
        source=SyncSource.GITHUB.value,
        title="New ML paper released",
        url="https://example.com",
        summary="A new ML paper",
        relevance_score=0.9,
        tags=["ml", "research", "opportunity"],
    )
    plugin.engine.ingest_change(
        source=SyncSource.ARXIV.value,
        title="ArXiv paper on transformers",
        url="https://arxiv.org",
        summary="Transformer improvements",
        relevance_score=0.8,
        tags=["research"],
    )
    plugin.engine.ingest_change(
        source=SyncSource.GITHUB.value,
        title="Random noise",
        url="https://example.com",
        summary="noise",
        relevance_score=0.2,
    )
    _pass("Ingested 3 changes")

    # Get relevant
    relevant = plugin.engine.get_relevant_changes(min_relevance=0.5)
    assert len(relevant) == 2
    _pass(f"Found {len(relevant)} relevant changes (min_relevance=0.5)")

    # Get by source
    gh = plugin.engine.get_changes_by_source(SyncSource.GITHUB.value)
    assert len(gh) == 2
    _pass(f"GitHub changes: {len(gh)}")

    # Get opportunities
    opps = plugin.engine.get_opportunities()
    assert len(opps) == 1
    _pass(f"Found {len(opps)} opportunities")

    # Sync check
    assert plugin.engine.should_sync(SyncSource.GITHUB.value)
    plugin.engine.record_sync(SyncSource.GITHUB.value)
    _pass("Recorded GitHub sync timestamp")

    # Stats
    stats = plugin.engine.get_stats()
    _pass(f"Stats: {stats}")



async def test_5_e2e():
    """Test 5: E2E with all Phase 6 plugins in the kernel."""
    header("Test 5: E2E Kernel Integration")

    from core.runtime.kernel import HermesKernel, KernelConfig
    config = KernelConfig()
    kernel = HermesKernel(config)
    await kernel.boot()

    # Check which Phase 6 plugins are available (some may be refactored)
    phase6_plugins = ["evolution_safety_loop", "benchmark_db", "self_improvement_boundary", "world_sync"]
    loaded = [name for name in phase6_plugins if name in kernel._plugins]
    _pass(f"Phase 6 plugins loaded: {len(loaded)}/{len(phase6_plugins)}: {loaded}")

    # Use evolution_safety_loop
    esl = kernel._plugins.get("evolution_safety_loop")
    if esl:
        mod = esl.engine.submit_modification(
            mod_type="procedure", description="e2e test",
            blast_radius=2, reversibility=0.95,
            value_alignment_score=0.95, test_coverage=0.9,
            rollback_plan="rollback procedure",
        )
        assert mod.approved
        _pass("Evolution safety: e2e mod approved")

    # Use benchmark_db
    bdb = kernel._plugins.get("benchmark_db")
    if bdb:
        run = bdb.engine.record_run("e2e_bench", score=0.85)
        _pass(f"Benchmark DB: recorded run {run.run_id}")

    # Use self_improvement_boundary
    sib = kernel._plugins.get("self_improvement_boundary")
    if sib:
        assert sib.engine.can_change("skill_library")
        _pass("Self-improvement boundary: skill_library changeable")

    # Use world_sync
    ws = kernel._plugins.get("world_sync")
    if ws:
        change = ws.engine.ingest_change(
            "github", "E2E test change", "https://e2e", "test", 0.5
        )
        _pass(f"World sync: ingested change {change.change_id}")

    # All healthy
    for name in loaded:
        plugin = kernel._plugins.get(name)
        if plugin and hasattr(plugin, "health"):
            health = await plugin.health()
            assert health.get("status") == "healthy", f"{name} unhealthy: {health}"

    _pass("All loaded Phase 6 plugins report healthy")

    await kernel.shutdown()


async def main():
    print("\n" + "=" * 70)
    print("  PHASE 6 TEST SUITE — Evolution")
    print("=" * 70)

    tests = [
        ("Test 1: Evolution Safety Loop", test_1_evolution_safety_loop),
        ("Test 2: Benchmark DB", test_2_benchmark_db),
        ("Test 3: Self-Improvement Boundary", test_3_self_improvement_boundary),
        ("Test 4: World Sync", test_4_world_sync),
        ("Test 5: E2E Integration", test_5_e2e),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            _fail(name, str(e))
            failed += 1

    print("\n" + "=" * 70)
    print(f"  PHASE 6 RESULTS: {passed}/{passed+failed} passed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
