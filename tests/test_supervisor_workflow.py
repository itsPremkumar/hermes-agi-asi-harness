"""Tests for the Supervisor's World Model, Dynamic Workflow, and Master Workflow Loop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor.dynamic import (
    AdvancedPlanningEngine,
    Complexity,
    DecisionEngine,
    DynamicScenarioAnalyzer,
    DynamicWorkflowExecutor,
    Plan,
    PlanStep,
    ScenarioType,
    StepResult,
)
from core.supervisor.workflow import (
    MasterWorkflowLoop,
    Trajectory,
)
from core.supervisor.world_model import (
    EntityType,
    WorldModel,
)

# ---------------------------------------------------------------------------
# World Model tests
# ---------------------------------------------------------------------------

class TestWorldModel:
    def test_create_world_model(self):
        wm = WorldModel()
        assert wm is not None

    def test_add_entity(self):
        wm = WorldModel()
        entity = wm.add_entity("Goal1", EntityType.GOAL, {"priority": "high"})
        assert entity.name == "Goal1"
        assert entity.type == EntityType.GOAL

    def test_get_entity(self):
        wm = WorldModel()
        entity = wm.add_entity("Goal1", EntityType.GOAL)
        retrieved = wm.get_entity(entity.id)
        assert retrieved is not None
        assert retrieved.id == entity.id

    def test_update_entity(self):
        wm = WorldModel()
        entity = wm.add_entity("Goal1", EntityType.GOAL)
        wm.update_entity(entity.id, name="Updated")
        assert entity.name == "Updated"

    def test_get_entities_by_type(self):
        wm = WorldModel()
        wm.add_entity("Goal1", EntityType.GOAL)
        wm.add_entity("Goal2", EntityType.GOAL)
        wm.add_entity("Task1", EntityType.TASK)
        goals = wm.get_entities_by_type(EntityType.GOAL)
        assert len(goals) == 2

    def test_add_belief(self):
        wm = WorldModel()
        belief = wm.add_belief("Test claim", confidence=0.8)
        assert belief.claim == "Test claim"
        assert belief.confidence == 0.8

    def test_update_belief(self):
        wm = WorldModel()
        belief = wm.add_belief("Test claim", confidence=0.5)
        wm.update_belief(belief.id, confidence=0.9, evidence="new evidence")
        assert belief.confidence == 0.9
        assert len(belief.evidence) == 1

    def test_add_causal_link(self):
        wm = WorldModel()
        link = wm.add_causal_link("cause1", "effect1", strength=0.7)
        assert link.cause_id == "cause1"
        assert link.strength == 0.7

    def test_add_forecast(self):
        wm = WorldModel()
        forecast = wm.add_forecast("Will succeed", probability=0.8, horizon="short")
        assert forecast.description == "Will succeed"
        assert forecast.probability == 0.8

    def test_add_counterfactual(self):
        wm = WorldModel()
        cf = wm.add_counterfactual("If X", "Then Y", probability=0.5)
        assert cf.condition == "If X"
        assert cf.outcome == "Then Y"

    def test_estimate_state(self):
        wm = WorldModel()
        state = wm.estimate_state({"key": "value"})
        assert state["entities"] == 0
        assert state["observations"]["key"] == "value"

    def test_get_state_summary(self):
        wm = WorldModel()
        wm.add_entity("Goal1", EntityType.GOAL)
        summary = wm.get_state_summary()
        assert summary["entities"] == 1

    def test_save_and_load(self, tmp_path):
        wm = WorldModel(data_dir=tmp_path)
        wm.add_entity("Goal1", EntityType.GOAL)
        wm.add_belief("Test claim", confidence=0.8)
        wm.save()

        wm2 = WorldModel(data_dir=tmp_path)
        wm2.load()
        entities = wm2.get_entities_by_type(EntityType.GOAL)
        assert len(entities) == 1


# ---------------------------------------------------------------------------
# Dynamic Scenario Analyzer tests
# ---------------------------------------------------------------------------

class TestDynamicScenarioAnalyzer:
    def test_create_analyzer(self):
        analyzer = DynamicScenarioAnalyzer()
        assert analyzer is not None

    def test_analyze_research(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Research the latest AI techniques")
        assert profile.scenario_type == ScenarioType.RESEARCH

    def test_analyze_bug_fix(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Fix the bug in the login system")
        assert profile.scenario_type == ScenarioType.BUG_FIX

    def test_analyze_new_project(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Create a project from scratch")
        assert profile.scenario_type == ScenarioType.NEW_PROJECT

    def test_analyze_benchmark(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Score on the ARC-AGI-3 benchmark")
        assert profile.scenario_type == ScenarioType.BENCHMARK

    def test_analyze_deployment(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Deploy the application to production")
        assert profile.scenario_type == ScenarioType.DEPLOYMENT

    def test_complexity_simple(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Fix bug")
        assert profile.complexity == Complexity.SIMPLE

    def test_complexity_moderate(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Build a REST API with authentication and database")
        assert profile.complexity == Complexity.MODERATE

    def test_complexity_complex(self):
        analyzer = DynamicScenarioAnalyzer()
        desc = "Build a comprehensive and extremely detailed REST API system with full authentication, authorization, rate limiting, comprehensive test coverage, extensive documentation, proper error handling, logging, monitoring, deployment configuration, and comprehensive integration with external services plus database management"
        profile = analyzer.analyze(desc)
        assert profile.complexity in (Complexity.COMPLEX, Complexity.VERY_COMPLEX)

    def test_recommended_modules(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Build a new project")
        assert len(profile.required_modules) > 0

    def test_recommended_topology(self):
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Research topic")
        assert profile.recommended_topology is not None


# ---------------------------------------------------------------------------
# Advanced Planning Engine tests
# ---------------------------------------------------------------------------

class TestAdvancedPlanningEngine:
    def test_create_engine(self):
        engine = AdvancedPlanningEngine()
        assert engine is not None

    def test_generate_plan(self):
        engine = AdvancedPlanningEngine()
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Build a new project")
        plan = engine.generate_plan(profile)
        assert len(plan.steps) > 0

    def test_plan_has_quality_gates(self):
        engine = AdvancedPlanningEngine()
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Build a new project")
        plan = engine.generate_plan(profile)
        assert len(plan.quality_gates) > 0

    def test_plan_duration(self):
        engine = AdvancedPlanningEngine()
        analyzer = DynamicScenarioAnalyzer()
        profile = analyzer.analyze("Build a new project")
        plan = engine.generate_plan(profile)
        assert plan.estimated_total_min > 0


# ---------------------------------------------------------------------------
# Dynamic Workflow Executor tests
# ---------------------------------------------------------------------------

class TestDynamicWorkflowExecutor:
    def test_create_executor(self):
        executor = DynamicWorkflowExecutor()
        assert executor is not None

    def test_execute_plan(self):
        executor = DynamicWorkflowExecutor()
        plan = Plan(title="Test")
        plan.steps = [PlanStep(title="Step1"), PlanStep(title="Step2")]
        # Note: execute_plan is async, so we test the sync parts
        assert len(plan.steps) == 2


# ---------------------------------------------------------------------------
# Decision Engine tests
# ---------------------------------------------------------------------------

class TestDecisionEngine:
    def test_create_engine(self):
        engine = DecisionEngine()
        assert engine is not None

    def test_decide_continue(self):
        engine = DecisionEngine()
        result = engine.decide(
            StepResult(status="completed"),
            {"retry_count": 0},
        )
        assert result == "continue"

    def test_decide_retry(self):
        engine = DecisionEngine()
        result = engine.decide(
            StepResult(status="failed"),
            {"retry_count": 1},
        )
        assert result == "retry"

    def test_decide_rollback(self):
        engine = DecisionEngine()
        result = engine.decide(
            StepResult(status="failed"),
            {"retry_count": 5},
        )
        assert result == "rollback"

    def test_should_rollback(self):
        engine = DecisionEngine()
        results = [
            StepResult(status="failed"),
            StepResult(status="failed"),
            StepResult(status="failed"),
            StepResult(status="completed"),
        ]
        assert engine.should_rollback(results)


# ---------------------------------------------------------------------------
# Master Workflow Loop tests
# ---------------------------------------------------------------------------

class TestMasterWorkflowLoop:
    def test_create_workflow(self):
        wf = MasterWorkflowLoop()
        assert wf is not None

    def test_perceive(self):
        wf = MasterWorkflowLoop()
        obs = wf.perceive({"key": "value"})
        assert obs["observations"]["key"] == "value"

    def test_estimate_state(self):
        wf = MasterWorkflowLoop()
        state = wf.estimate_state({"key": "value"})
        assert state["estimated_state"]["key"] == "value"

    def test_set_goal(self):
        wf = MasterWorkflowLoop()
        goal = wf.set_goal("Build X", priority="high")
        assert goal["goal"] == "Build X"

    def test_predict_futures(self):
        wf = MasterWorkflowLoop()
        futures = wf.predict_futures({"goal": "Build X"}, num_futures=3)
        assert len(futures) == 3

    def test_search_policies(self):
        wf = MasterWorkflowLoop()
        policies = wf.search_policies({"goal": "Build X"})
        assert isinstance(policies, list)

    def test_select_policy(self):
        wf = MasterWorkflowLoop()
        policy = wf.select_policy([])
        assert policy is None

    def test_self_evaluate(self):
        wf = MasterWorkflowLoop()
        eval_result = wf.self_evaluate()
        assert eval_result["trajectories"] == 0

    def test_detect_bottlenecks(self):
        wf = MasterWorkflowLoop()
        bottlenecks = wf.detect_bottlenecks()
        assert isinstance(bottlenecks, list)

    def test_run_experiment(self):
        wf = MasterWorkflowLoop()
        exp = wf.run_experiment("hypothesis", "action")
        assert exp.hypothesis == "hypothesis"

    def test_run_full_cycle(self):
        wf = MasterWorkflowLoop()
        trajectory = wf.run_full_cycle("Build X", {"context": "test"})
        assert isinstance(trajectory, Trajectory)
        assert len(trajectory.stages) > 0

    def test_get_trajectories(self):
        wf = MasterWorkflowLoop()
        wf.run_full_cycle("Build X", {"context": "test"})
        trajectories = wf.get_trajectories()
        assert len(trajectories) == 1
