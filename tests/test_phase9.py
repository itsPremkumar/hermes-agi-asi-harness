"""
Test Suite for Phase 9: Cognitive Extensions

Tests:
1. Causal Model: add relations, record states, simulate intervention, downstream effects
2. Capability Graph: record success/failure, dependencies, gap analysis
3. Self-Model: record execution, bottlenecks, recommendations
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    print(f"\n{'='*60}")
    print("  PHASE 9: Cognitive Extensions Tests")
    print(f"{'='*60}")

    results = []

    # Test 1: Causal Model
    print("\n[1/3] Causal Model Engine...")
    try:
        from plugins.causal_model import create as cm_create

        plugin = await cm_create()
        await plugin.load()

        # Add causal relations
        plugin.engine.add_causal_relation("rain", "wet_ground", "causes", 0.9)
        plugin.engine.add_causal_relation("wet_ground", "slippery", "causes", 0.7)
        plugin.engine.add_causal_relation("sprinkler", "wet_ground", "causes", 0.8)

        # Record states
        plugin.engine.record_state("rain", True, "observed")
        plugin.engine.record_state("wet_ground", True, "inferred")

        # Simulate intervention
        sim = plugin.engine.simulate_intervention(
            {"rain": 1.0},
            "What if it rains?"
        )
        assert sim.predicted_outcome is not None

        # Get downstream effects
        effects = plugin.engine.get_downstream_effects("rain")
        assert "wet_ground" in effects or len(effects) > 0

        # Get causal relations
        relations = plugin.engine.get_causal_relations("rain")
        assert len(relations) >= 1

        stats = plugin.engine.get_stats()
        assert stats["causal_relations"] >= 2

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Causal Model", True, f"relations={stats['causal_relations']}"))
        print(f"  ✓ Causal Model: {stats['causal_relations']} relations")
    except Exception as e:
        results.append(("Causal Model", False, str(e)[:100]))
        print(f"  ✗ Causal Model failed: {e}")

    # Test 2: Capability Graph
    print("\n[2/3] Capability Graph...")
    try:
        from plugins.capability_graph import create as cg_create

        plugin = await cg_create()
        await plugin.load()

        # Record capabilities
        for _ in range(10):
            plugin.graph.record_success("coding")
        for _ in range(3):
            plugin.graph.record_failure("planning", "timeout")
        for _ in range(5):
            plugin.graph.record_success("research")

        # Set dependencies
        plugin.graph.set_dependency("coding", requires="planning")
        plugin.graph.set_dependency("research", improves="planning")

        # Get weakest
        weakest = plugin.graph.get_weakest(2)
        assert len(weakest) >= 1

        # Get gap analysis
        gaps = plugin.graph.get_gap_analysis()
        assert "gaps" in gaps

        stats = plugin.graph.get_stats()
        assert stats["total"] >= 3

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Capability Graph", True, f"capabilities={stats['total']}"))
        print(f"  ✓ Capability Graph: {stats['total']} capabilities")
    except Exception as e:
        results.append(("Capability Graph", False, str(e)[:100]))
        print(f"  ✗ Capability Graph failed: {e}")

    # Test 3: Self-Model
    print("\n[3/3] Self-Model...")
    try:
        from plugins.self_model import create as sm_create

        plugin = await sm_create()
        await plugin.load()

        # Record executions
        for _ in range(8):
            plugin.engine.record_execution("coding", True, strategy="tdd", model="qwen", resource_cost=0.5)
        for _ in range(2):
            plugin.engine.record_execution("coding", False, failure_mode="timeout")
        for _ in range(5):
            plugin.engine.record_execution("planning", True, strategy="dag", resource_cost=0.3)

        # Get weakest
        weakest = plugin.engine.get_weakest(2)
        assert len(weakest) >= 1

        # Detect bottlenecks
        bottlenecks = plugin.engine.detect_bottlenecks()
        assert isinstance(bottlenecks, list)

        # Get recommendation
        rec = plugin.engine.get_recommendation("coding")
        assert "recommendation" in rec

        # Get profile
        profile = plugin.engine.get_profile()
        assert "capabilities" in profile

        stats = plugin.engine.get_stats()
        assert stats["total"] >= 2

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Self-Model", True, f"capabilities={stats['total']}"))
        print(f"  ✓ Self-Model: {stats['total']} capabilities")
    except Exception as e:
        results.append(("Self-Model", False, str(e)[:100]))
        print(f"  ✗ Self-Model failed: {e}")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Phase 9 Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
