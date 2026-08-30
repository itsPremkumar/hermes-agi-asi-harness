"""Tests for the Hermes Supervisor Harness (legacy — kept for compatibility)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor import (
    SupervisorState, TaskType, Task, Goal,
    Supervisor,
)
from core.supervisor.memory import (
    PersistentMemory, MemoryEntry, MemoryType, Experience,
)
from core.supervisor.evaluation import (
    EvaluationGate, CodeEvaluationGate, BenchmarkEvaluationGate,
    EvaluationResult,
)
from core.supervisor.variation import (
    VariationOperator, Candidate,
)
from core.supervisor.orchestrator import (
    MultiAgentOrchestrator, Agent, AgentRole, Topology,
)
from core.supervisor.planner import Planner
from core.supervisor.dispatcher import Dispatcher
from core.supervisor.monitor import Monitor
from core.supervisor.research import ResearchAgent


# ---------------------------------------------------------------------------
# Goal tests
# ---------------------------------------------------------------------------

class TestGoal:
    def test_create_goal(self):
        goal = Goal(title="Test Goal", description="A test goal")
        assert goal.title == "Test Goal"
        assert goal.status == "pending"

    def test_create_sub_goal(self):
        sg = Task(title="Sub", description="A sub-goal")
        assert sg.status == "pending"
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

    def test_decompose_research(self):
        planner = Planner()
        goal = Goal(title="Research X", description="Research the topic")
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
        sg = Task(title="Test", description="Test sub-goal")
        dispatch_id = dispatcher.dispatch(sg, {})
        assert dispatch_id is not None
        assert len(dispatch_id) == 8


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
        assert len(goal.tasks) > 0

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

    def test_run_goal(self):
        supervisor = Supervisor()
        goal = supervisor.add_goal("Test Goal", "A test goal")
        supervisor.run(goal.id)
        assert goal.status == "completed"

    def test_get_status(self):
        supervisor = Supervisor()
        supervisor.add_goal("Test Goal", "A test goal")
        status = supervisor.get_status()
        assert status["total_goals"] == 1


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_lifecycle(self, tmp_path):
        """Test a full goal lifecycle."""
        supervisor = Supervisor(data_dir=tmp_path)
        goal = supervisor.add_goal("Build Feature X", "Build a new feature")
        assert len(goal.tasks) > 0
        supervisor.run(goal.id)
        assert goal.status == "completed"

    def test_multiple_goals(self, tmp_path):
        """Test managing multiple goals."""
        supervisor = Supervisor(data_dir=tmp_path)
        g1 = supervisor.add_goal("Research X", "Research the topic")
        g2 = supervisor.add_goal("Build Y", "Build the feature")
        g3 = supervisor.add_goal("Deploy Z", "Deploy to production")
        assert len(supervisor.list_goals()) == 3
        for g in [g1, g2, g3]:
            supervisor.run(g.id)
        status = supervisor.get_status()
        assert status["completed_goals"] == 3
