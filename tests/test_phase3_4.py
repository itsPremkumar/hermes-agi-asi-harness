"""
Phase 3+4 Test Suite — Autonomous Execution + Multi-Agent

Tests:
1. Watchdog: event recording, anomaly detection, loop detection, health report
2. Economic Ledger: budget setting, token usage, time tracking, budget checks
3. Independent Critic: dual-critic review, decision making, conflict resolution
4. Debate Protocol: debate rounds, voting, executive judgment
5. E2E: full mission with watchdog + economic ledger + critic + debate
"""

import os
os.environ.setdefault("HERMES_HOME", "/tmp/hermes_phase3_4_test")

import sys
import asyncio
from pathlib import Path
from unittest.mock import patch as mock_patch

sys.path.insert(0, str(Path(__file__).parent))

from core.runtime.kernel import HermesKernel, KernelConfig


def header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print('='*70)


def test_pass(name):
    print(f"  ✓ {name}")


def test_fail(name, err):
    print(f"  ✗ {name}: {err}")


async def test_1_watchdog():
    """Test 1: Watchdog anomaly detection."""
    header("Test 1: Watchdog Anomaly Detection")

    from plugins.watchdog import WatchdogPlugin, AnomalyType, create as wd_create
    plugin = await wd_create()
    await plugin.load()
    await plugin.start()

    # Test basic recording
    plugin.record_event("test_event", {"data": "value"})
    test_pass("record_event doesn't crash")

    # Test loop detection
    for i in range(8):
        plugin.record_event("loopy_event")
    anomalies = plugin.engine.detect_anomalies()
    has_loop = any(a.type == AnomalyType.AGENT_LOOP.value for a in anomalies)
    assert has_loop, f"Expected loop anomaly, got: {anomalies}"
    test_pass("Loop detection works (8 events in window)")

    # Test health
    health = await plugin.health()
    assert "metrics" in health, f"Health missing metrics: {health}"
    test_pass(f"Health report: {health.get('status')}")

    await plugin.stop()
    return True


async def test_2_economic_ledger():
    """Test 2: Economic Ledger budget management."""
    header("Test 2: Economic Ledger Budget Management")

    from plugins.economic_ledger import EconomicLedgerPlugin, MissionBudget, EconomicLedger
    plugin = EconomicLedgerPlugin()
    plugin.engine = EconomicLedger()

    # Set a budget
    budget = MissionBudget(
        token_limit=1000,
        time_limit_seconds=60,
        monetary_limit=10.0,
    )
    plugin.engine.set_budget("mission_001", budget)
    test_pass("Budget set")

    # Record token usage
    plugin.engine.record_token_usage("mission_001", 500, cost=5.0)
    test_pass("Recorded 500 tokens ($5.0)")

    # Check budget
    status = plugin.engine.check_budget("mission_001")
    assert status["within_budget"], f"Should be within budget: {status}"
    assert status["utilization"]["tokens"] == 0.5, f"Token utilization should be 0.5: {status}"
    test_pass(f"Budget check: {status['utilization']}")

    # Record time
    plugin.engine.record_time("mission_001", 30.0)
    status = plugin.engine.check_budget("mission_001")
    assert status["utilization"]["time"] == 0.5, f"Time utilization should be 0.5: {status}"
    test_pass(f"Time tracked: {status['utilization']['time']}")

    # Expected value
    ev = plugin.engine.expected_value(expected_benefit=100.0, cost=10.0, probability=0.5)
    assert ev == 40.0, f"EV should be 40.0, got {ev}"
    test_pass(f"Expected value: $40.0 (0.5 * $100 - $10)")

    # Test budget exhaustion
    plugin.engine.record_token_usage("mission_001", 600, cost=5.0)
    status = plugin.engine.check_budget("mission_001")
    assert "token_budget_90_percent" in status["alerts"], f"Expected alert: {status}"
    test_pass(f"Budget alert fired: {status['alerts']}")

    return True


async def test_3_independent_critic():
    """Test 3: Independent Critic dual-critic system."""
    header("Test 3: Independent Critic")

    from plugins.independent_critic import create as crit_create
    plugin = await crit_create()
    await plugin.load()

    # Use dual_critique
    decision = plugin.engine.dual_critique(
        content="Use Redis for caching API responses",
        criteria=["performance", "reliability", "cost"],
        critic_a_id="critic_a",
        critic_b_id="critic_b",
    )
    review1, review2 = decision.critic_reviews[0], decision.critic_reviews[1]
    test_pass(f"Two independent reviews: {review1.critic_id} vs {review2.critic_id}")

    # Check reviews
    assert 0 <= review1.confidence <= 1, f"Confidence out of range: {review1.confidence}"
    test_pass(f"Review 1: verdict={review1.verdict.value}, confidence={review1.confidence:.2f}")

    assert 0 <= review2.confidence <= 1, f"Confidence out of range: {review2.confidence}"
    test_pass(f"Review 2: verdict={review2.verdict.value}, confidence={review2.confidence:.2f}")

    # Verify decision
    assert decision.decision in ["accept", "revise", "reject"], f"Bad decision: {decision.decision}"
    test_pass(f"Executive decision: {decision.decision} (consensus: {decision.consensus})")

    # Test critique method
    single_review = plugin.engine.critique(
        content="Use SQL for all data",
        criteria=["security", "scalability"],
        critic_id="solo_critic",
    )
    test_pass(f"Single critique: verdict={single_review.verdict.value}, confidence={single_review.confidence:.2f}")

    # Get history
    history = plugin.engine.get_history()
    assert len(history) >= 1, f"Expected at least 1 decision in history, got {len(history)}"
    test_pass(f"History: {len(history)} decisions")

    return True


async def test_4_debate_protocol():
    """Test 4: Debate Protocol with executive judgment."""
    header("Test 4: Debate Protocol")

    from plugins.debate_protocol import create as deb_create
    plugin = await deb_create()
    await plugin.load()

    # Run a full debate
    outcome = plugin.engine.run_full_debate(
        topic="Should we adopt microservices?",
        initial_proposal="Yes, adopt microservices for better scalability",
        rounds=2,
    )
    test_pass(f"Debate {outcome.debate_id} completed in {outcome.duration_seconds:.2f}s")

    # Verify outcome structure
    assert outcome.winner is not None, "No winner decided"
    test_pass(f"Winner: {outcome.winner.value}")

    assert outcome.executive_decision, "No executive decision"
    test_pass(f"Executive decision: {outcome.executive_decision}")

    # Check arguments
    assert len(outcome.arguments) >= 4, f"Expected 4+ arguments, got {len(outcome.arguments)}"
    test_pass(f"Recorded {len(outcome.arguments)} arguments")

    # Stats
    stats = plugin.engine.get_stats()
    assert stats["total_debates"] == 1
    test_pass(f"Stats: {stats}")

    return True


async def test_5_e2e():
    """Test 5: End-to-end with all Phase 3+4 plugins in the kernel."""
    header("Test 5: End-to-End Kernel Integration")

    config = KernelConfig()
    kernel = HermesKernel(config)
    await kernel.boot()

    # Verify all 4 new plugins are loaded
    for name in ["watchdog", "economic_ledger", "independent_critic", "debate_protocol"]:
        assert name in kernel._plugins, f"{name} not loaded in kernel"
    test_pass("All 4 Phase 3+4 plugins loaded in kernel")

    # Use watchdog
    if kernel._plugins.get("watchdog"):
        kernel._plugins["watchdog"].record_event("e2e_test")
        test_pass("Watchdog recorded E2E event")

    # Use economic ledger
    if kernel._plugins.get("economic_ledger"):
        from plugins.economic_ledger import MissionBudget
        budget = MissionBudget(token_limit=5000, time_limit_seconds=300, monetary_limit=0.0)
        kernel._plugins["economic_ledger"].engine.set_budget("e2e_mission", budget)
        kernel._plugins["economic_ledger"].engine.record_token_usage("e2e_mission", 100, cost=0.001)
        status = kernel._plugins["economic_ledger"].engine.check_budget("e2e_mission")
        assert status["within_budget"], f"Not within budget: {status}"
        test_pass(f"Economic ledger: {status['utilization']}")

    # Use independent critic
    if kernel._plugins.get("independent_critic"):
        decision = kernel._plugins["independent_critic"].engine.dual_critique(
            content="use Redis for caching",
            criteria=["performance", "cost"],
            critic_a_id="critic_a",
            critic_b_id="critic_b",
        )
        test_pass(f"Independent critic: decision={decision.decision}, consensus={decision.consensus}")

    # Use debate protocol
    if kernel._plugins.get("debate_protocol"):
        outcome = kernel._plugins["debate_protocol"].engine.run_full_debate(
            "Should we deploy on Friday?",
            "Yes, deploy early on Friday to catch issues before weekend",
            rounds=1,
        )
        assert outcome.winner is not None
        test_pass(f"Debate {outcome.debate_id}: winner = {outcome.winner.value}")

    # Verify health
    for name in ["watchdog", "economic_ledger", "independent_critic", "debate_protocol"]:
        plugin = kernel._plugins.get(name)
        if plugin and hasattr(plugin, "health"):
            health = await plugin.health()
            assert health.get("status") in ("healthy", "degraded", "ok"), f"{name} unhealthy: {health}"

    test_pass("All plugins report healthy status")

    await kernel.shutdown()
    return True


async def main():
    print("\n" + "=" * 70)
    print("  PHASE 3+4 TEST SUITE — Autonomous Execution + Multi-Agent")
    print("=" * 70)

    tests = [
        ("Test 1: Watchdog", test_1_watchdog),
        ("Test 2: Economic Ledger", test_2_economic_ledger),
        ("Test 3: Independent Critic", test_3_independent_critic),
        ("Test 4: Debate Protocol", test_4_debate_protocol),
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
            test_fail(name, str(e))
            failed += 1

    print("\n" + "=" * 70)
    print(f"  PHASE 3+4 RESULTS: {passed}/{passed+failed} passed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
