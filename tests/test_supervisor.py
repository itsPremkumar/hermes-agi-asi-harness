"""Tests for the Hermes Supervisor Harness."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor import (
    GoalStatus, SubGoal, Goal,
    ResearchAgent, Planner, Dispatcher, Monitor, Supervisor,
)


# ---------------------------------------------------------------------------
# Goal tests
# ---------------------------------------------------------------------------

class TestGoal:
    def test_create_goal(self):
        goal = Goal(title="Test Goal", description="A test goal")
        assert goal.title == "Test Goal"
        assert goal.status == GoalStatus.PENDING
        assert len(goal.sub_goals) == 0

    def test_create_sub_goal(self):
        sg = SubGoal(title="Sub", description="A sub-goal")
        assert sg.status == GoalStatus.PENDING
        assert sg.priority == 0


# ---------------------------------------------------------------------------
# Planner tests
# ---------------------------------------------------------------------------

class TestPlanner:
    def test_create_planner(self):
        planner = Planner()
        assert planner is not None

    def test_classify_research(self):
        planner = Planner()
        goal = Goal(title="Research X", description="Research the topic")
        assert planner._classify_goal(goal) == "research"

    def test_classify_development(self):
        planner = Planner()
        goal = Goal(title="Build X", description="Build a new feature")
        assert planner._classify_goal(goal) == "development"

    def test_classify_benchmark(self):
        planner = Planner()
        goal = Goal(title="Benchmark X", description="Score on benchmark")
        assert planner._classify_goal(goal) == "benchmark"

    def test_classify_deployment(self):
        planner = Planner()
        goal = Goal(title="Deploy X", description="Deploy to production")
        assert planner._classify_goal(goal) == "deployment"

    def test_decompose_research(self):
        planner = Planner()
        goal = Goal(title="Research X", description="Research the topic")
        sub_goals = planner.decompose(goal)
        assert len(sub_goals) >= 3
        assert sub_goals[0].title == "Initial search"

    def test_decompose_development(self):
        planner = Planner()
        goal = Goal(title="Build X", description="Build a new feature")
        sub_goals = planner.decompose(goal)
        assert len(sub_goals) >= 5
        assert sub_goals[0].title == "Requirements analysis"

    def test_decompose_benchmark(self):
        planner = Planner()
        goal = Goal(title="Benchmark X", description="Score on benchmark")
        sub_goals = planner.decompose(goal)
        assert len(sub_goals) >= 4

    def test_decompose_deployment(self):
        planner = Planner()
        goal = Goal(title="Deploy X", description="Deploy to production")
        sub_goals = planner.decompose(goal)
        assert len(sub_goals) >= 4

    def test_decompose_generic(self):
        planner = Planner()
        goal = Goal(title="Do X", description="Do something")
        sub_goals = planner.decompose(goal)
        assert len(sub_goals) >= 3


# ---------------------------------------------------------------------------
# Dispatcher tests
# ---------------------------------------------------------------------------

class TestDispatcher:
    def test_create_dispatcher(self):
        dispatcher = Dispatcher()
        assert dispatcher is not None

    def test_dispatch(self):
        dispatcher = Dispatcher()
        sg = SubGoal(title="Test", description="Test sub-goal")
        dispatch_id = dispatcher.dispatch(sg, {})
        assert dispatch_id is not None
        assert len(dispatch_id) == 8

    def test_choose_method_research(self):
        dispatcher = Dispatcher()
        sg = SubGoal(title="Search", description="Search the web")
        assert dispatcher._choose_method(sg) == "research_agent"

    def test_choose_method_coding(self):
        dispatcher = Dispatcher()
        sg = SubGoal(title="Implement", description="Write the code")
        assert dispatcher._choose_method(sg) == "coding_agent"

    def test_choose_method_testing(self):
        dispatcher = Dispatcher()
        sg = SubGoal(title="Test", description="Verify the feature works correctly")
        assert dispatcher._choose_method(sg) == "testing_agent"

    def test_choose_method_deployment(self):
        dispatcher = Dispatcher()
        sg = SubGoal(title="Deploy", description="Deploy to production")
        assert dispatcher._choose_method(sg) == "deployment_agent"

    def test_choose_method_writing(self):
        dispatcher = Dispatcher()
        sg = SubGoal(title="Document", description="Write documentation")
        assert dispatcher._choose_method(sg) == "writing_agent"

    def test_get_dispatch_status(self):
        dispatcher = Dispatcher()
        sg = SubGoal(title="Test", description="Test")
        dispatch_id = dispatcher.dispatch(sg, {})
        status = dispatcher.get_dispatch_status(dispatch_id)
        assert status is not None
        assert status["status"] == "dispatched"

    def test_update_dispatch(self):
        dispatcher = Dispatcher()
        sg = SubGoal(title="Test", description="Test")
        dispatch_id = dispatcher.dispatch(sg, {})
        dispatcher.update_dispatch(dispatch_id, "completed", "Done")
        status = dispatcher.get_dispatch_status(dispatch_id)
        assert status["status"] == "completed"
        assert status["result"] == "Done"


# ---------------------------------------------------------------------------
# Monitor tests
# ---------------------------------------------------------------------------

class TestMonitor:
    def test_create_monitor(self):
        monitor = Monitor()
        assert monitor is not None

    def test_checkpoint(self):
        monitor = Monitor()
        monitor.checkpoint("goal_1")
        assert "goal_1" in monitor._checkpoints

    def test_is_stalled_false(self):
        monitor = Monitor(stall_timeout=300.0)
        monitor.checkpoint("goal_1")
        assert not monitor.is_stalled("goal_1")

    def test_is_stalled_true(self):
        monitor = Monitor(stall_timeout=0.0)
        monitor.checkpoint("goal_1")
        import time
        time.sleep(0.01)
        assert monitor.is_stalled("goal_1")

    def test_get_progress(self):
        monitor = Monitor()
        goal = Goal(title="Test", description="Test")
        goal.sub_goals = [
            SubGoal(title="SG1", status=GoalStatus.COMPLETED),
            SubGoal(title="SG2", status=GoalStatus.COMPLETED),
            SubGoal(title="SG3", status=GoalStatus.PENDING),
        ]
        progress = monitor.get_progress(goal)
        assert progress["total"] == 3
        assert progress["completed"] == 2
        assert progress["pending"] == 1


# ---------------------------------------------------------------------------
# ResearchAgent tests
# ---------------------------------------------------------------------------

class TestResearchAgent:
    def test_create_researcher(self):
        researcher = ResearchAgent()
        assert researcher is not None

    def test_research(self):
        researcher = ResearchAgent()
        result = researcher.research("test topic", depth=1)
        assert result["topic"] == "test topic"
        assert result["depth"] == 1

    def test_save_and_load_research(self, tmp_path):
        researcher = ResearchAgent(memory_path=tmp_path)
        research = {"topic": "test", "findings": ["finding1"]}
        researcher.save_research("goal_1", research)
        loaded = researcher.load_research("goal_1")
        assert loaded is not None
        assert loaded["topic"] == "test"


# ---------------------------------------------------------------------------
# Supervisor tests
# ---------------------------------------------------------------------------

class TestSupervisor:
    def test_create_supervisor(self):
        supervisor = Supervisor()
        assert supervisor is not None
        assert not supervisor.is_active

    def test_add_goal(self):
        supervisor = Supervisor()
        goal = supervisor.add_goal("Test Goal", "A test goal")
        assert goal.title == "Test Goal"
        assert len(goal.sub_goals) > 0

    def test_get_goal(self):
        supervisor = Supervisor()
        goal = supervisor.add_goal("Test Goal", "A test goal")
        retrieved = supervisor.get_goal(goal.id)
        assert retrieved is not None
        assert retrieved.id == goal.id

    def test_list_goals(self):
        supervisor = Supervisor()
        supervisor.add_goal("Goal 1", "First goal")
        supervisor.add_goal("Goal 2", "Second goal")
        goals = supervisor.list_goals()
        assert len(goals) == 2

    def test_execute_goal(self):
        supervisor = Supervisor()
        goal = supervisor.add_goal("Test Goal", "A test goal")
        supervisor.execute_goal(goal.id)
        assert goal.status == GoalStatus.COMPLETED

    def test_get_status(self):
        supervisor = Supervisor()
        supervisor.add_goal("Test Goal", "A test goal")
        status = supervisor.get_status()
        assert status["total_goals"] == 1

    def test_save_and_load_state(self, tmp_path):
        supervisor = Supervisor(data_dir=tmp_path)
        goal = supervisor.add_goal("Test Goal", "A test goal")
        supervisor.save_state()

        # Create new supervisor and load state
        supervisor2 = Supervisor(data_dir=tmp_path)
        supervisor2.load_state()
        goals = supervisor2.list_goals()
        assert len(goals) == 1
        assert goals[0].title == "Test Goal"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_lifecycle(self, tmp_path):
        """Test a full goal lifecycle."""
        supervisor = Supervisor(data_dir=tmp_path)

        # Add a development goal
        goal = supervisor.add_goal("Build Feature X", "Build a new feature for the project")

        # Verify sub-goals were created
        assert len(goal.sub_goals) > 0

        # Execute the goal
        supervisor.execute_goal(goal.id)

        # Verify completion
        assert goal.status == GoalStatus.COMPLETED
        for sg in goal.sub_goals:
            assert sg.status == GoalStatus.COMPLETED

    def test_multiple_goals(self, tmp_path):
        """Test managing multiple goals."""
        supervisor = Supervisor(data_dir=tmp_path)

        g1 = supervisor.add_goal("Research X", "Research the topic")
        g2 = supervisor.add_goal("Build Y", "Build the feature")
        g3 = supervisor.add_goal("Deploy Z", "Deploy to production")

        assert len(supervisor.list_goals()) == 3

        # Execute all
        for g in [g1, g2, g3]:
            supervisor.execute_goal(g.id)

        # Verify all completed
        status = supervisor.get_status()
        assert status["completed_goals"] == 3

    def test_goal_with_metadata(self, tmp_path):
        """Test goal with metadata."""
        supervisor = Supervisor(data_dir=tmp_path)
        goal = supervisor.add_goal(
            "Test Goal",
            "A test goal",
            priority="high",
            assignee="agent_1",
        )
        assert goal.metadata["priority"] == "high"
        assert goal.metadata["assignee"] == "agent_1"
