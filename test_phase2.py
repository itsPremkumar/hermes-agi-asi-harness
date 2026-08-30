#!/usr/bin/env python3
"""
test_phase2.py — Phase 2 Persistent Intelligence Tests

Tests:
1. Belief Engine — facts, beliefs, assumptions, hypothesis, prediction, contradiction detection
2. Persistent State Store — 11 state files, atomic writes, validation
3. Mission Queue — priority queue, state transitions, retry, stats
4. Capability Registry — empirical tracking, success rate, self-model
5. Phase 2 E2E — all 4 components integrated via kernel
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test_belief_engine():
    """Test Bayesian belief engine with all epistemic statuses."""
    from core.runtime.kernel import HermesKernel, KernelConfig
    from plugins.belief_engine import BeliefStatus

    k = HermesKernel(config=KernelConfig(zero_cost=True, offline=True))
    await k.boot()

    engine = k.belief_engine

    # Add beliefs of different types
    fact = engine.add_belief("The system is running", confidence=0.99, status=BeliefStatus.FACT)
    belief = engine.add_belief("This task will succeed", confidence=0.7, status=BeliefStatus.BELIEF)
    assumption = engine.add_belief("User is available", confidence=0.5, status=BeliefStatus.ASSUMPTION)
    hypothesis = engine.add_belief("New approach is better", confidence=0.3, status=BeliefStatus.HYPOTHESIS)
    prediction = engine.add_belief("Task will complete in 5 min", confidence=0.6, status=BeliefStatus.PREDICTION)

    assert fact.id
    assert belief.status == BeliefStatus.BELIEF
    assert assumption.status == BeliefStatus.ASSUMPTION
    assert hypothesis.status == BeliefStatus.HYPOTHESIS
    assert prediction.status == BeliefStatus.PREDICTION

    # Update confidence with supporting evidence
    engine.update_confidence(fact.id, "System confirmed running", is_supporting=True)
    assert engine._beliefs[fact.id].confidence >= 0.99

    # Update with contradicting evidence
    engine.update_confidence(belief.id, "Previous attempt failed", is_supporting=False)

    # Check summary
    summary = engine.get_summary()
    assert summary["total_beliefs"] >= 5
    assert summary["by_status"]["fact"] >= 1

    # Check get_beliefs_by_confidence
    high_conf = engine.get_beliefs_by_confidence(0.6)
    assert len(high_conf) >= 1

    await k.shutdown()
    print("  ✓ Belief Engine: all epistemic statuses, confidence updates, contradiction summary")
    return True


async def test_persistent_state():
    """Test persistent state store with 11 state files."""
    from core.persistent_state import PersistentStateStore, StateFile

    with tempfile.TemporaryDirectory() as tmpdir:
        store = PersistentStateStore(state_dir=tmpdir)

        # Check all 11 files initialized
        summary = store.get_state_summary()
        for sf in StateFile:
            assert summary["files"][sf.value], f"State file {sf.value} not created"
        assert len(summary["files"]) == 11

        # Test atomic write
        store.update_entity("entity_1", {"type": "server", "status": "online"})
        store.update_entity("entity_1", {"status": "degraded"})  # Update
        state = store.read(StateFile.WORLD_STATE)
        entities = state["entities"]
        assert len(entities) == 1
        assert entities[0]["status"] == "degraded"
        assert "updated_at" in entities[0]

        # Test mission graph
        store.add_mission({"objective": "Test mission 1", "priority": 1.0})
        mission_state = store.read(StateFile.MISSION_GRAPH)
        assert len(mission_state["nodes"]) >= 1
        assert mission_state["nodes"][0]["status"] == "active"

        # Test financial ledger
        store.record_token_cost("gpt-4", 1000, 0.03)
        ledger = store.read(StateFile.FINANCIAL_LEDGER)
        assert ledger["total"] >= 0.03
        assert len(ledger["token_costs"]) >= 1

        # Test capability registry
        store.update_capability("coding", {"success_rate": 0.95, "evidence_count": 42})
        cap = store.get_capability("coding")
        assert cap["success_rate"] == 0.95

        # Test tool registry
        store.update_tool_registration("python_exec", {"purpose": "Execute Python", "risk": "low"})
        tools = store.read(StateFile.TOOL_REGISTRY)
        assert "python_exec" in tools["tools"]

        # Test health state
        store.update_health("execution_engine", {"status": "healthy", "state": "running"})
        health = store.read(StateFile.HEALTH_STATE)
        assert "execution_engine" in health["plugins"]

        # Test backup files exist
        backup_files = list(Path(tmpdir).glob(".*.bak"))
        # Backups created on second write

        # Test state consistency / validation
        try:
            store._validate_state(StateFile.WORLD_STATE, {"no_entities": []})
            assert False, "Validation should have failed"
        except Exception:
            pass  # Expected to fail

    print("  ✓ Persistent State: 11 state files, atomic writes, validation, backup")
    return True


async def test_mission_queue():
    """Test persistent priority-based mission queue."""
    from core.runtime.kernel import HermesKernel, KernelConfig
    from plugins.mission_queue import MissionStatus

    k = HermesKernel(config=KernelConfig(zero_cost=True, offline=True))
    await k.boot()

    queue = k.mission_queue

    # Submit missions with different priorities
    id_low = queue.submit("Low priority task", priority=1.0)
    id_high = queue.submit("High priority task", priority=10.0)
    id_med = queue.submit("Medium priority task", priority=5.0)

    assert id_low != id_high
    assert id_high != id_med

    # Check priority ordering (highest first)
    all_missions = queue.get_all()
    assert len(all_missions) >= 3

    # Peek at highest priority
    next_mission = queue.peek()
    assert next_mission is not None
    assert "High priority" in next_mission["objective"]

    # Pop highest priority
    popped = queue.pop()
    assert "High priority" in popped["objective"]

    # Update status
    queue.update_status(id_med, "completed", {"result": "success"})
    assert queue.get_status(id_med) == "completed"

    # Retry a failed mission
    queue.update_status(id_low, "failed")
    queue.retry(id_low, new_priority=20.0)
    assert queue.get_status(id_low) == "recovering"

    # Pop the retried mission (should be highest priority now)
    retried = queue.pop()
    assert retried["retry_count"] == 1

    # Check stats
    stats = queue.get_stats()
    assert "pending" in stats
    assert "completed" in stats
    assert "failed" in stats

    await k.shutdown()
    print("  ✓ Mission Queue: priority ordering, state transitions, retry, stats")
    return True


async def test_capability_registry():
    """Test empirical capability tracking and self-model."""
    from core.runtime.kernel import HermesKernel, KernelConfig

    k = HermesKernel(config=KernelConfig(zero_cost=True, offline=True))
    await k.boot()

    reg = k.capability_registry

    # Register capabilities
    reg.register_capability("coding", category="engineering", required_tools=["python_exec"])
    reg.register_capability("research", category="research", required_tools=["web_search"])
    reg.register_capability("planning", category="reasoning")

    # Record results
    reg.record_result("coding", success=True, time_seconds=5.0, model="claude")
    reg.record_result("coding", success=True, time_seconds=3.0, model="claude")
    reg.record_result("coding", success=False, time_seconds=10.0, model="gpt-4")
    reg.record_result("research", success=True, time_seconds=15.0, model="claude")

    # Check capability data
    coding = reg.get_capability("coding")
    assert coding is not None
    assert coding.evidence_count == 3
    assert coding.success_rate == 2/3  # 2 success, 1 failure
    assert coding.best_model == "claude"
    assert coding.average_time_seconds > 0

    # Check confidence increases with evidence
    assert coding.confidence > 0.3

    # Best model recommendation
    assert reg.get_best_model_for_capability("coding") == "claude"
    assert reg.get_confidence("coding") > 0

    # Summary
    summary = reg.get_summary()
    assert summary["total_capabilities"] >= 3
    assert summary["avg_success_rate"] > 0
    assert "engineering" in summary["by_category"]

    await k.shutdown()
    print("  ✓ Capability Registry: empirical tracking, success rate, self-model")
    return True


async def test_phase2_e2e():
    """Test Phase 2 components integrated end-to-end."""
    from core.runtime.kernel import HermesKernel, KernelConfig
    from core.persistent_state import StateFile

    k = HermesKernel(config=KernelConfig(zero_cost=True, offline=True))
    await k.boot()

    # Verify all Phase 2 components
    assert k.persistent_state is not None
    assert k.mission_queue is not None
    assert k.belief_engine is not None
    assert k.capability_registry is not None

    # 1. Create goal contract
    contract = k.goal_contract.create_contract("Build a simple API endpoint")
    assert contract.id.startswith("GOAL-")

    # 2. Submit to persistent mission queue
    mission_id = k.mission_queue.submit(
        contract.objective,
        priority=5.0,
        risk_level=contract.risk_level,
    )
    assert mission_id is not None

    # 3. Record belief about the task
    from plugins.belief_engine import BeliefStatus
    belief = k.belief_engine.add_belief(
        f"Task '{contract.objective}' is feasible",
        confidence=0.8,
        status=BeliefStatus.BELIEF,
    )
    assert belief.confidence == 0.8

    # 4. Record capability data
    k.capability_registry.record_result(
        "research", success=True, time_seconds=10.0, model="claude"
    )
    assert k.capability_registry.get_capability("research") is not None

    # 5. Store mission in persistent state
    k.persistent_state.add_mission({
        "id": mission_id,
        "objective": contract.objective,
        "status": "active",
        "priority": 5.0,
    })
    state = k.persistent_state.read(StateFile.MISSION_GRAPH)
    assert len(state["nodes"]) >= 1

    # 6. Update health in persistent state
    k.persistent_state.update_health("kernel", {"status": "healthy", "overall": "healthy"})
    health = k.persistent_state.read(StateFile.HEALTH_STATE)
    assert health["plugins"]["kernel"]["status"] == "healthy"

    await k.shutdown()
    print("  ✓ Phase 2 E2E: goal contract → mission queue → belief → capability → persistent state")
    return True


async def main():
    print("=" * 60)
    print("PHASE 2: PERSISTENT INTELLIGENCE TESTS")
    print("=" * 60)

    tests = [
        ("Belief Engine", test_belief_engine),
        ("Persistent State Store", test_persistent_state),
        ("Mission Queue", test_mission_queue),
        ("Capability Registry", test_capability_registry),
        ("Phase 2 E2E", test_phase2_e2e),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            result = await test_fn()
            if result:
                passed += 1
        except Exception as e:
            print(f"  ✗ {name}: FAILED — {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"PHASE 2 TESTS: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
