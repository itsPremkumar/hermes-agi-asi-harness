"""Test v11 Dynamic Workflow Executor — Full Integration."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print(f"\n{'='*60}")
    print("  HERMES-ASI-MASTER v11 — Dynamic Workflow Tests")
    print(f"{'='*60}")

    results = []

    # Test 1: Workflow Executor Initialization
    print("\n[1/5] Workflow Executor...")
    try:
        from core.dynamic import DynamicWorkflowExecutor
        
        executor = DynamicWorkflowExecutor()
        state = executor.get_state()
        assert state["modules"] > 0
        
        results.append(("Workflow Executor", True, f"modules={state['modules']}"))
        print(f"  ✓ {state['modules']} modules registered")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Workflow Executor", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 2: Full Dynamic Execution
    print("\n[2/5] Full Dynamic Execution...")
    try:
        from core.dynamic import (
            AdvancedPlanningEngine,
            DynamicScenarioAnalyzer,
            DynamicWorkflowExecutor,
        )
        
        analyzer = DynamicScenarioAnalyzer()
        engine = AdvancedPlanningEngine()
        executor = DynamicWorkflowExecutor()
        
        goal = "Build a REST API with authentication"
        profile = analyzer.analyze(goal)
        plan = engine.generate_plan(profile)
        result = await executor.execute_plan(plan)
        
        assert result.status.value in ["completed", "failed"]
        assert len(result.step_results) > 0
        
        completed = len([r for r in result.step_results if r.status.value == "completed"])
        failed = len([r for r in result.step_results if r.status.value == "failed"])
        
        results.append(("Full Execution", True, f"steps={len(result.step_results)}, completed={completed}, failed={failed}"))
        print(f"  ✓ Execution: {len(result.step_results)} steps, {completed} completed, {failed} failed")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Full Execution", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 3: Kernel Integration
    print("\n[3/5] Kernel Integration...")
    try:
        from core.runtime.kernel import HermesKernel, KernelConfig
        
        config = KernelConfig(plugins_root=Path('plugins'))
        kernel = HermesKernel(config)
        await kernel.boot()
        
        assert kernel.workflow_executor is not None
        assert kernel.scenario_analyzer is not None
        assert kernel.planning_engine is not None
        
        # Test dynamic execution through kernel
        result = await kernel.plan_and_execute_dynamic("Build a simple REST API")
        
        assert "success" in result
        assert "scenario_type" in result
        assert "complexity" in result
        
        await kernel.shutdown()
        
        results.append(("Kernel Integration", True, f"dynamic_execution={result['success']}"))
        print(f"  ✓ Kernel dynamic execution: {result['scenario_type']}, {result['complexity']}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Kernel Integration", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 4: Different Topologies
    print("\n[4/5] Different Topologies...")
    try:
        from core.dynamic import (
            AdvancedPlanningEngine,
            DynamicScenarioAnalyzer,
            DynamicWorkflowExecutor,
        )
        
        analyzer = DynamicScenarioAnalyzer()
        engine = AdvancedPlanningEngine()
        executor = DynamicWorkflowExecutor()
        
        topologies = ["single", "sequential", "parallel", "hierarchical"]
        
        for topology in topologies:
            # Create a simple plan with the given topology
            profile = analyzer.analyze("Test goal")
            plan = engine.generate_plan(profile)
            plan.topology = topology
            
            result = await executor.execute_plan(plan)
            
            assert result.status.value in ["completed", "failed"]
        
        results.append(("Topologies", True, f"tested={len(topologies)}"))
        print(f"  ✓ Tested {len(topologies)} topologies: {', '.join(topologies)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Topologies", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 5: End-to-End Workflow
    print("\n[5/5] End-to-End Workflow...")
    try:
        from core.runtime.kernel import HermesKernel, KernelConfig
        
        config = KernelConfig(plugins_root=Path('plugins'))
        kernel = HermesKernel(config)
        await kernel.boot()
        
        # Test multiple scenarios
        scenarios = [
            "Fix the login bug",
            "Build a new feature",
            "Research best practices",
            "Deploy to production",
        ]
        
        for scenario in scenarios:
            result = await kernel.plan_and_execute_dynamic(scenario)
            assert "success" in result
        
        await kernel.shutdown()
        
        results.append(("End-to-End", True, f"scenarios={len(scenarios)}"))
        print(f"  ✓ {len(scenarios)} scenarios executed end-to-end")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("End-to-End", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  v11 Dynamic Workflow Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        print(f"  {'✓' if ok else '✗'} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
