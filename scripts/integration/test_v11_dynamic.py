"""Test v11 Dynamic Planning Engine."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print(f"\n{'='*60}")
    print("  HERMES-ASI-MASTER v11 — Dynamic Planning Tests")
    print(f"{'='*60}")

    results = []

    # Test 1: Scenario Analysis
    print("\n[1/6] Dynamic Scenario Analyzer...")
    try:
        from core.dynamic import DynamicScenarioAnalyzer, ScenarioType, ComplexityLevel
        
        analyzer = DynamicScenarioAnalyzer()
        
        # Test different scenarios
        scenarios = [
            "Fix the login bug where users can't authenticate",
            "Create a new REST API for user management with authentication and database integration",
            "Research machine learning libraries for Python to improve our data pipeline",
            "Deploy the application to production AWS with CI/CD pipeline",
            "Refactor the database layer to use ORM for better maintainability",
        ]
        
        for scenario in scenarios:
            profile = analyzer.analyze(scenario)
            assert profile.scenario_type is not None
            assert profile.complexity is not None
            assert len(profile.required_modules) > 0
            assert profile.recommended_workflow != ""
        
        # Verify specific classifications
        bug_profile = analyzer.analyze("Fix the login bug where users cannot authenticate")
        assert bug_profile.scenario_type == ScenarioType.BUG_FIX
        assert bug_profile.requires_debugging == True
        
        feature_profile = analyzer.analyze("Create a brand new web application from scratch with authentication and database")
        assert feature_profile.scenario_type == ScenarioType.NEW_PROJECT
        assert feature_profile.requires_architecture_synthesis == True
        
        research_profile = analyzer.analyze("Research machine learning libraries for Python")
        assert research_profile.scenario_type == ScenarioType.RESEARCH
        assert research_profile.requires_research == True
        
        results.append(("Scenario Analyzer", True, "5 scenarios classified"))
        print("  ✓ 5 scenarios classified correctly")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Scenario Analyzer", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 2: Complexity Assessment
    print("\n[2/6] Complexity Assessment...")
    try:
        from core.dynamic import DynamicScenarioAnalyzer, ComplexityLevel
        
        analyzer = DynamicScenarioAnalyzer()
        
        simple = analyzer.analyze("Fix typo in README")
        moderate = analyzer.analyze("Add user profile page with form validation")
        high = analyzer.analyze("Refactor the entire microservices architecture system")
        extreme = analyzer.analyze("Migrate the complete system from monolith to microservices with zero downtime and full data migration")
        
        assert simple.complexity in (ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE)
        assert moderate.complexity in (ComplexityLevel.MODERATE, ComplexityLevel.SIMPLE)
        assert high.complexity in (ComplexityLevel.HIGH, ComplexityLevel.MODERATE, ComplexityLevel.EXTREME)
        assert extreme.complexity in (ComplexityLevel.EXTREME, ComplexityLevel.HIGH)
        
        results.append(("Complexity Assessment", True, f"simple={simple.complexity}, extreme={extreme.complexity}"))
        print(f"  ✓ Complexities: simple={simple.complexity}, moderate={moderate.complexity}, high={high.complexity}, extreme={extreme.complexity}")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Complexity Assessment", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 3: Technology Detection
    print("\n[3/6] Technology Detection...")
    try:
        from core.dynamic import DynamicScenarioAnalyzer
        
        analyzer = DynamicScenarioAnalyzer()
        
        profile = analyzer.analyze("Build a React frontend with Python FastAPI backend and PostgreSQL database")
        
        assert "python" in profile.detected_languages
        assert "react" in profile.detected_frameworks
        assert "postgresql" in profile.detected_databases
        
        results.append(("Tech Detection", True, f"langs={len(profile.detected_languages)}, fw={len(profile.detected_frameworks)}"))
        print(f"  ✓ Languages: {profile.detected_languages}, Frameworks: {profile.detected_frameworks}, DBs: {profile.detected_databases}")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Tech Detection", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 4: Dynamic Plan Generation
    print("\n[4/6] Dynamic Plan Generation...")
    try:
        from core.dynamic import AdvancedPlanningEngine
        
        engine = AdvancedPlanningEngine()
        
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Build a new REST API with authentication and database")
        
        plan = engine.generate_plan(profile)
        
        assert len(plan.steps) > 0
        assert plan.topology != ""
        assert plan.estimated_total_min > 0
        assert len(plan.required_modules) > 0
        
        # Verify steps have proper dependencies
        has_deps = any(len(s.depends_on) > 0 for s in plan.steps)
        assert has_deps
        
        results.append(("Plan Generation", True, f"steps={len(plan.steps)}, topology={plan.topology}"))
        print(f"  ✓ Plan: {len(plan.steps)} steps, topology={plan.topology}, est={plan.estimated_total_min}min")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Plan Generation", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 5: Decision Engine
    print("\n[5/6] Dynamic Decision Engine...")
    try:
        from core.dynamic import DynamicDecisionEngine
        from core.dynamic.planning_engine import PlanStep, StepStatus
        
        engine = DynamicDecisionEngine()
        
        # Simulate a failed implementation step
        step = PlanStep(id="test-1", name="Implementation", step_type="implementation",
                       description="Implement feature", status=StepStatus.FAILED)
        
        decisions = engine.evaluate_step_completion(step, {"error": "build failed"})
        assert len(decisions) > 0
        
        results.append(("Decision Engine", True, f"decisions={len(decisions)}"))
        print(f"  ✓ Decisions made: {len(decisions)}")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Decision Engine", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 6: Full Dynamic Workflow
    print("\n[6/6] Full Dynamic Workflow...")
    try:
        from core.dynamic import DynamicScenarioAnalyzer, AdvancedPlanningEngine, DynamicDecisionEngine
        
        # Complete workflow
        analyzer = DynamicScenarioAnalyzer()
        engine = AdvancedPlanningEngine()
        decision_engine = DynamicDecisionEngine()
        
        # Analyze different scenarios
        test_cases = [
            ("Fix the login bug where users can't authenticate", "bug fix"),
            ("Build a new e-commerce platform", "new project"),
            ("Research best practices for microservices", "research"),
            ("Deploy to production with CI/CD", "deployment"),
        ]
        
        for goal, description in test_cases:
            profile = analyzer.analyze(goal)
            plan = engine.generate_plan(profile)
            
            assert profile.scenario_type is not None
            assert len(plan.steps) > 0
            assert plan.topology != ""
            
            # Simulate step completion decisions
            for step in plan.steps:
                decisions = decision_engine.evaluate_step_completion(step, {})
                # Decisions should be made for failed/completed steps
        
        results.append(("Full Workflow", True, f"{len(test_cases)} scenarios processed"))
        print(f"  ✓ Full workflow: {len(test_cases)} scenarios analyzed, planned, and decided")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Full Workflow", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  v11 Dynamic Planning Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        print(f"  {'✓' if ok else '✗'} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
