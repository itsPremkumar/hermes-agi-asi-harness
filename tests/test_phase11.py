"""
Test Suite for Phase 11: Intelligence Scaling

Tests:
1. Model Router V2: register models, record results, get best model
2. Compute Scaling: budget per difficulty, can spawn agent, can call tool
3. Agent Fabric: create agents, lifecycle, pause/resume
4. Failure Intelligence: record failure, generate counterfactuals, recurring
5. Calibration: record predictions, Brier score, calibration curve
6. Anti-Goodhart: evaluate candidate, Pareto dominance
7. Bottleneck Detection: set scores, detect bottlenecks
8. Evolution Archive: create candidates, evaluate, Pareto frontier
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    print(f"\n{'='*60}")
    print("  PHASE 11: Intelligence Scaling Tests")
    print(f"{'='*60}")

    results = []

    # Test 1: Model Router V2
    print("\n[1/8] Model Router V2...")
    try:
        from plugins.model_router_v2 import create as mr_create

        plugin = await mr_create()
        await plugin.load()

        # Register models
        await plugin.register_model(model_id="qwen-fast", task_classes=["coding", "research"])
        await plugin.register_model(model_id="llama-code", task_classes=["coding", "math"])

        # Record results
        for _ in range(5):
            await plugin.record_result("qwen-fast", "coding", True, latency=1.0, cost=0.01)
        for _ in range(2):
            await plugin.record_result("llama-code", "coding", True, latency=2.0, cost=0.02)

        # Get best model
        best = await plugin.get_best_model("coding")
        assert best is not None

        stats = plugin.engine.get_stats()
        assert stats["total_records"] >= 2

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Model Router V2", True, f"records={stats['total_records']}"))
        print(f"  ✓ Model Router V2: {stats['total_records']} records, best={best}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Model Router V2", False, str(e)[:100]))
        print(f"  ✗ Model Router V2 failed: {e}")

    # Test 2: Compute Scaling
    print("\n[2/8] Compute Scaling...")
    try:
        from plugins.compute_scaling import create as cs_create

        plugin = await cs_create()
        await plugin.load()

        # Get budget
        budget = await plugin.get_budget("coding", difficulty=0.8)
        assert budget.reasoning_level == "high"

        # Start task
        plugin.controller.start_task("task-001", budget)

        # Check can spawn
        can_spawn = await plugin.can_spawn_agent("task-001")
        assert can_spawn

        # Record usage
        plugin.controller.record_agent_spawn("task-001")
        plugin.controller.record_tool_call("task-001")

        stats = plugin.controller.get_stats()
        assert stats["active_tasks"] >= 1

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Compute Scaling", True, f"active={stats['active_tasks']}"))
        print(f"  ✓ Compute Scaling: budget={budget.reasoning_level}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Compute Scaling", False, str(e)[:100]))
        print(f"  ✗ Compute Scaling failed: {e}")

    # Test 3: Agent Fabric
    print("\n[3/8] Agent Fabric...")
    try:
        from plugins.agent_fabric import create as af_create

        plugin = await af_create()
        await plugin.load()

        # Create agent
        agent = await plugin.create("coder")
        assert agent.role == "coder"
        assert agent.status == "created"

        # Initialize
        plugin.registry.initialize_agent(agent.agent_id, mission_id="M001")
        plugin.registry.assign_task(agent.agent_id, "T001")
        plugin.registry.start_execution(agent.agent_id)

        # Pause/resume
        plugin.registry.pause_agent(agent.agent_id)
        assert plugin.registry.get_agent(agent.agent_id).status == "paused"
        plugin.registry.resume_agent(agent.agent_id)
        assert plugin.registry.get_agent(agent.agent_id).status == "executing"

        # Complete
        plugin.registry.complete_agent(agent.agent_id, artifacts=["patch/123"])

        stats = await plugin.get_stats()
        assert stats["total"] >= 1

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Agent Fabric", True, f"agents={stats['total']}"))
        print(f"  ✓ Agent Fabric: {stats['total']} agents")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Agent Fabric", False, str(e)[:100]))
        print(f"  ✗ Agent Fabric failed: {e}")

    # Test 4: Failure Intelligence
    print("\n[4/8] Failure Intelligence...")
    try:
        from plugins.failure_intelligence import create as fi_create

        plugin = await fi_create()
        await plugin.load()

        # Record failure
        failure = await plugin.record_failure(
            mission_id="M001",
            task_id="T001",
            expected="success",
            actual="timeout",
            failure_class="tool_execution",
            root_cause="network_timeout",
            impact_score=0.8,
        )

        # Generate counterfactuals
        cfs = await plugin.generate_counterfactuals(failure.id)
        assert len(cfs) >= 1

        # Record recovery
        plugin.engine.record_recovery(failure.id, "retry_with_backoff")

        # Get recurring
        await plugin.get_recurring()

        stats = plugin.engine.get_failure_summary()
        assert stats["total"] >= 1

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Failure Intelligence", True, f"failures={stats['total']}, cfs={len(cfs)}"))
        print(f"  ✓ Failure Intelligence: {stats['total']} failures, {len(cfs)} counterfactuals")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Failure Intelligence", False, str(e)[:100]))
        print(f"  ✗ Failure Intelligence failed: {e}")

    # Test 5: Calibration
    print("\n[5/8] Calibration...")
    try:
        from plugins.calibration import create as cal_create

        plugin = await cal_create()
        await plugin.load()

        # Record predictions
        for _ in range(5):
            await plugin.record("coding", 0.9, True)
        await plugin.record("coding", 0.9, False)

        # Brier score
        brier = await plugin.get_brier_score("coding")
        assert 0.0 <= brier <= 1.0

        # Calibration curve
        curve = await plugin.get_curve("coding")
        assert len(curve) >= 1

        stats = plugin.tracker.get_stats()
        assert stats["total"] >= 5

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Calibration", True, f"brier={brier:.4f}"))
        print(f"  ✓ Calibration: Brier={brier:.4f}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Calibration", False, str(e)[:100]))
        print(f"  ✗ Calibration failed: {e}")

    # Test 6: Anti-Goodhart
    print("\n[6/8] Anti-Goodhart...")
    try:
        from plugins.anti_goodhart import create as ag_create

        plugin = await ag_create()
        await plugin.load()

        # Record metrics
        for _ in range(5):
            plugin.engine.record_metric("success_rate", 0.8)
            plugin.engine.record_metric("cost", 0.01)

        # Evaluate candidate
        result = await plugin.evaluate(
            candidate_id="C001",
            metrics={"success_rate": 0.85, "cost": 0.005},
        )
        assert "passed" in result

        stats = plugin.engine.get_stats()
        assert stats["metrics_tracked"] >= 2

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Anti-Goodhart", True, f"passed={result['passed']}"))
        print(f"  ✓ Anti-Goodhart: passed={result['passed']}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Anti-Goodhart", False, str(e)[:100]))
        print(f"  ✗ Anti-Goodhart failed: {e}")

    # Test 7: Bottleneck Detection
    print("\n[7/8] Bottleneck Detection...")
    try:
        from plugins.bottleneck_detector import create as bd_create

        plugin = await bd_create()
        await plugin.load()

        # Set scores
        await plugin.set_score("planning", 0.4)
        await plugin.set_score("coding", 0.9)
        await plugin.set_score("research", 0.7)

        # Increment failures
        plugin.engine.increment_failure("planning")
        plugin.engine.increment_failure("planning")

        # Detect bottlenecks
        bottlenecks = await plugin.detect()
        assert len(bottlenecks) >= 1
        assert bottlenecks[0]["capability"] == "planning"

        stats = plugin.engine.get_stats()
        assert stats["weakest"] == "planning"

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Bottleneck Detection", True, f"weakest={stats['weakest']}"))
        print(f"  ✓ Bottleneck Detection: weakest={stats['weakest']}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Bottleneck Detection", False, str(e)[:100]))
        print(f"  ✗ Bottleneck Detection failed: {e}")

    # Test 8: Evolution Archive
    print("\n[8/8] Evolution Archive...")
    try:
        from plugins.evolution_archive import create as ea_create

        plugin = await ea_create()
        await plugin.load()

        # Create candidates
        c1 = await plugin.create_candidate(
            parent="baseline",
            change_type="planner",
            hypothesis_id="H001",
            changed_components=["planner.py"],
            expected_gain=0.1,
        )
        c2 = await plugin.create_candidate(
            parent="baseline",
            change_type="memory",
            hypothesis_id="H002",
            changed_components=["memory.py"],
            expected_gain=0.05,
        )

        # Evaluate
        await plugin.evaluate(c1.id, dev_score=0.85, holdout_score=0.80, novel_score=0.75, regression=False, safety_pass=True)
        await plugin.evaluate(c2.id, dev_score=0.90, holdout_score=0.40, novel_score=0.30, regression=True, safety_pass=True)

        # Get Pareto
        pareto = await plugin.get_pareto()
        assert isinstance(pareto, list)

        stats = plugin.archive.get_stats()
        assert stats["total"] >= 2

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Evolution Archive", True, f"candidates={stats['total']}"))
        print(f"  ✓ Evolution Archive: {stats['total']} candidates")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Evolution Archive", False, str(e)[:100]))
        print(f"  ✗ Evolution Archive failed: {e}")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Phase 11 Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
