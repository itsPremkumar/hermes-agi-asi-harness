"""Tests for Goal Compiler, Decomposer, Dependency Graph, Assignment Engine, Goal Manager, and Replanning Engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor.goal_compiler import (
    Complexity,
    GoalCompiler,
    GoalType,
)
from core.supervisor.goal_decomposer import (
    GoalDecomposer,
    GoalLevel,
)
from core.supervisor.goal_manager import (
    AssignmentEngine,
    GoalDependencyGraph,
    GoalManager,
    ReplanningEngine,
    Worker,
)

# ---------------------------------------------------------------------------
# Goal Compiler tests
# ---------------------------------------------------------------------------

class TestGoalCompiler:
    def test_create_compiler(self):
        compiler = GoalCompiler()
        assert compiler is not None

    def test_compile_goal(self):
        compiler = GoalCompiler()
        contract = compiler.compile("Build a REST API")
        assert contract.title == "Build a REST API"
        assert contract.goal_type == GoalType.BUILD

    def test_classify_build(self):
        compiler = GoalCompiler()
        assert compiler._classify_goal("Build a new feature") == GoalType.BUILD
        assert compiler._classify_goal("Create a project") == GoalType.BUILD

    def test_classify_research(self):
        compiler = GoalCompiler()
        assert compiler._classify_goal("Research the topic") == GoalType.RESEARCH
        assert compiler._classify_goal("Analyze the data") == GoalType.RESEARCH

    def test_classify_fix(self):
        compiler = GoalCompiler()
        assert compiler._classify_goal("Fix the bug") == GoalType.FIX
        assert compiler._classify_goal("Error in the system") == GoalType.FIX

    def test_classify_deploy(self):
        compiler = GoalCompiler()
        assert compiler._classify_goal("Deploy to production") == GoalType.DEPLOY
        assert compiler._classify_goal("Release the app") == GoalType.DEPLOY

    def test_complexity_simple(self):
        compiler = GoalCompiler()
        assert compiler._assess_complexity("Fix bug") == Complexity.SIMPLE

    def test_complexity_moderate(self):
        compiler = GoalCompiler()
        assert compiler._assess_complexity("Build a REST API with authentication and database") == Complexity.MODERATE

    def test_complexity_complex(self):
        compiler = GoalCompiler()
        desc = "Build a comprehensive and extremely detailed REST API system with full authentication, authorization, rate limiting, comprehensive test coverage, extensive documentation, proper error handling, logging, monitoring, deployment configuration, and comprehensive integration with external services plus database management"
        assert compiler._assess_complexity(desc) in (Complexity.COMPLEX, Complexity.VERY_COMPLEX)

    def test_success_criteria(self):
        compiler = GoalCompiler()
        contract = compiler.compile("Build a REST API")
        assert len(contract.success_criteria) > 0

    def test_deliverables(self):
        compiler = GoalCompiler()
        contract = compiler.compile("Build a REST API")
        assert len(contract.deliverables) > 0

    def test_risks(self):
        compiler = GoalCompiler()
        contract = compiler.compile("Build a REST API")
        assert len(contract.risks) > 0

    def test_to_dict(self):
        compiler = GoalCompiler()
        contract = compiler.compile("Build a REST API")
        data = contract.to_dict()
        assert "id" in data
        assert "title" in data
        assert "goal_type" in data


# ---------------------------------------------------------------------------
# Goal Decomposer tests
# ---------------------------------------------------------------------------

class TestGoalDecomposer:
    def test_create_decomposer(self):
        decomposer = GoalDecomposer()
        assert decomposer is not None

    def test_decompose_build(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Build a REST API")
        hierarchy = decomposer.decompose(contract)
        assert hierarchy is not None
        assert hierarchy.root_id is not None

    def test_hierarchy_has_mission(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Build a REST API")
        hierarchy = decomposer.decompose(contract)
        root = hierarchy.get_node(hierarchy.root_id)
        assert root.level == GoalLevel.MISSION

    def test_hierarchy_has_goals(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Build a REST API")
        hierarchy = decomposer.decompose(contract)
        root = hierarchy.get_node(hierarchy.root_id)
        assert len(root.children) > 0

    def test_hierarchy_has_subgoals(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Build a REST API")
        hierarchy = decomposer.decompose(contract)
        # Check that at least one goal has subgoals
        has_subgoals = False
        for node in hierarchy.nodes.values():
            if node.level == GoalLevel.GOAL and node.children:
                has_subgoals = True
                break
        assert has_subgoals

    def test_hierarchy_has_tasks(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Build a REST API")
        hierarchy = decomposer.decompose(contract)
        tasks = [n for n in hierarchy.nodes.values() if n.level == GoalLevel.TASK]
        assert len(tasks) > 0

    def test_get_ready_tasks(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Build a REST API")
        hierarchy = decomposer.decompose(contract)
        ready = hierarchy.get_ready_tasks()
        assert isinstance(ready, list)

    def test_get_progress(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Build a REST API")
        hierarchy = decomposer.decompose(contract)
        progress = hierarchy.get_progress()
        assert "total" in progress
        assert "completed" in progress
        assert "percent" in progress

    def test_re_decompose(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Build a REST API")
        hierarchy = decomposer.decompose(contract)

        # Get a goal node
        goal_node = None
        for node in hierarchy.nodes.values():
            if node.level == GoalLevel.GOAL:
                goal_node = node
                break

        if goal_node:
            new_subtasks = [("New Task 1", "Description 1"), ("New Task 2", "Description 2")]
            hierarchy = decomposer.re_decompose(hierarchy.id, goal_node.id, new_subtasks)
            assert len(goal_node.children) == 2

    def test_decompose_research(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Research the latest AI techniques")
        hierarchy = decomposer.decompose(contract)
        assert hierarchy is not None

    def test_decompose_fix(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Fix the bug in the login system")
        hierarchy = decomposer.decompose(contract)
        assert hierarchy is not None

    def test_decompose_deploy(self):
        compiler = GoalCompiler()
        decomposer = GoalDecomposer()
        contract = compiler.compile("Deploy the application to production")
        hierarchy = decomposer.decompose(contract)
        assert hierarchy is not None


# ---------------------------------------------------------------------------
# Goal Dependency Graph tests
# ---------------------------------------------------------------------------

class TestGoalDependencyGraph:
    def test_create_graph(self):
        graph = GoalDependencyGraph()
        assert graph is not None

    def test_add_dependency(self):
        graph = GoalDependencyGraph()
        graph.add_dependency("A", "B")
        deps = graph.get_dependencies("B")
        assert "A" in deps

    def test_get_dependents(self):
        graph = GoalDependencyGraph()
        graph.add_dependency("A", "B")
        dependents = graph.get_dependents("A")
        assert "B" in dependents

    def test_is_ready(self):
        graph = GoalDependencyGraph()
        graph.add_dependency("A", "B")
        assert graph.is_ready("B", ["A"])
        assert not graph.is_ready("B", [])

    def test_get_ready_goals(self):
        graph = GoalDependencyGraph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        ready = graph.get_ready_goals(["A", "B", "C"], ["A", "B"])
        assert "C" in ready

    def test_get_critical_path(self):
        graph = GoalDependencyGraph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        path = graph.get_critical_path("C")
        assert "A" in path
        assert "B" in path
        assert "C" in path


# ---------------------------------------------------------------------------
# Assignment Engine tests
# ---------------------------------------------------------------------------

class TestAssignmentEngine:
    def test_create_engine(self):
        engine = AssignmentEngine()
        assert engine is not None

    def test_register_worker(self):
        engine = AssignmentEngine()
        worker = Worker(name="Hermes-01", capabilities=["coding", "testing"])
        engine.register_worker(worker)
        assert engine.get_worker(worker.id) is not None

    def test_get_available_workers(self):
        engine = AssignmentEngine()
        worker = Worker(name="Hermes-01", capabilities=["coding"])
        engine.register_worker(worker)
        available = engine.get_available_workers()
        assert len(available) == 1

    def test_assign_task(self):
        engine = AssignmentEngine()
        worker = Worker(name="Hermes-01", capabilities=["coding", "testing"])
        engine.register_worker(worker)
        worker_id = engine.assign_task("task_1", ["coding"])
        assert worker_id is not None
        assert worker.status == "busy"

    def test_assign_task_no_worker(self):
        engine = AssignmentEngine()
        worker_id = engine.assign_task("task_1", ["coding"])
        assert worker_id is None

    def test_complete_task(self):
        engine = AssignmentEngine()
        worker = Worker(name="Hermes-01", capabilities=["coding"])
        engine.register_worker(worker)
        engine.assign_task("task_1", ["coding"])
        engine.complete_task(worker.id, True)
        assert worker.status == "idle"
        assert worker.total_tasks == 1
        assert worker.completed_tasks == 1

    def test_worker_capability_score(self):
        worker = Worker(name="Hermes-01", capabilities=["coding", "testing"])
        score = worker.capability_score(["coding", "security"])
        assert score == 0.5

    def test_worker_capability_score_full_match(self):
        worker = Worker(name="Hermes-01", capabilities=["coding", "testing"])
        score = worker.capability_score(["coding", "testing"])
        assert score == 1.0

    def test_get_worker_stats(self):
        engine = AssignmentEngine()
        worker = Worker(name="Hermes-01", capabilities=["coding"])
        engine.register_worker(worker)
        stats = engine.get_worker_stats()
        assert worker.id in stats


# ---------------------------------------------------------------------------
# Goal Manager tests
# ---------------------------------------------------------------------------

class TestGoalManager:
    def test_create_manager(self):
        manager = GoalManager()
        assert manager is not None

    def test_register_goal(self):
        manager = GoalManager()
        manager.register_goal("goal_1", {"title": "Test Goal"})
        health = manager.get_health("goal_1")
        assert health is not None

    def test_update_progress(self):
        manager = GoalManager()
        manager.register_goal("goal_1", {"title": "Test Goal"})
        manager.update_progress("goal_1", 0.5)
        health = manager.get_health("goal_1")
        assert health["progress"] == 0.5

    def test_update_health(self):
        manager = GoalManager()
        manager.register_goal("goal_1", {"title": "Test Goal"})
        manager.update_health("goal_1", risk=0.8)
        health = manager.get_health("goal_1")
        assert health["risk"] == 0.8

    def test_get_blockers(self):
        manager = GoalManager()
        manager.register_goal("goal_1", {"title": "Test Goal"})
        manager.update_health("goal_1", blockers=["dep_1"])
        blockers = manager.get_blockers("goal_1")
        assert "dep_1" in blockers

    def test_is_at_risk(self):
        manager = GoalManager()
        manager.register_goal("goal_1", {"title": "Test Goal"})
        manager.update_health("goal_1", risk=0.8)
        assert manager.is_at_risk("goal_1")

    def test_get_overall_health(self):
        manager = GoalManager()
        manager.register_goal("goal_1", {"title": "Test Goal"})
        manager.register_goal("goal_2", {"title": "Test Goal 2"})
        health = manager.get_overall_health()
        assert health["total"] == 2


# ---------------------------------------------------------------------------
# Replanning Engine tests
# ---------------------------------------------------------------------------

class TestReplanningEngine:
    def test_create_engine(self):
        engine = ReplanningEngine()
        assert engine is not None

    def test_needs_replanning(self):
        engine = ReplanningEngine()
        manager = GoalManager()
        graph = GoalDependencyGraph()
        # No goals, no replanning needed
        assert not engine.needs_replanning(manager, graph)

    def test_replan(self):
        engine = ReplanningEngine()
        manager = GoalManager()
        graph = GoalDependencyGraph()
        manager.register_goal("goal_1", {"title": "Test Goal"})
        manager.update_health("goal_1", risk=0.8)

        # Create a mock decomposer and hierarchy
        class MockDecomposer:
            pass

        class MockHierarchy:
            id = "h1"
            nodes = {}

        result = engine.replan(manager, graph, MockDecomposer(), MockHierarchy())
        assert "actions" in result

    def test_get_history(self):
        engine = ReplanningEngine()
        history = engine.get_history()
        assert isinstance(history, list)
