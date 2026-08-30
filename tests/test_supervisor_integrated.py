"""Tests for the LangGraph + DeepAgents integration."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor.langgraph_skeleton import (
    LangGraphSkeleton, SupervisorState, NodeName, EdgeCondition,
    build_default_graph, is_completed, is_stalled, has_more_steps, always_continue,
)
from core.supervisor.deepagent import (
    DeepAgent, InnerMonologue, MonologueStage,
    VirtualFileSystem, PlanningTool, Plan, SubAgentSpawner,
)
from core.supervisor.integrated import (
    plan_node, dispatch_node, monitor_node, adjust_node, evolve_node,
    IntegratedSupervisor,
)


# ---------------------------------------------------------------------------
# LangGraph Skeleton tests
# ---------------------------------------------------------------------------

class TestLangGraphSkeleton:
    def test_create_skeleton(self):
        graph = LangGraphSkeleton()
        assert graph is not None

    def test_register_node(self):
        graph = LangGraphSkeleton()
        graph.register_node("test", lambda s: s)
        assert "test" in graph._nodes

    def test_register_edge(self):
        graph = LangGraphSkeleton()
        graph.register_edge("a", "continue", "b", lambda s: True)
        assert "a" in graph._edges

    def test_run_graph(self):
        graph = LangGraphSkeleton(max_iterations=5)

        # Register simple nodes using correct names
        def start_node(s):
            s.goal_status = "completed"
            return s

        graph.register_node("plan", start_node)
        graph.register_node("complete", lambda s: s)

        # Register edges
        graph.register_edge("plan", "continue", "complete", always_continue)

        state = graph.run("test goal")
        assert state.goal_status == "completed"

    def test_build_default_graph(self):
        graph = build_default_graph(
            plan_handler=plan_node,
            dispatch_handler=dispatch_node,
            monitor_handler=monitor_node,
            adjust_handler=adjust_node,
            evolve_handler=evolve_node,
        )
        assert NodeName.PLAN.value in graph._nodes
        assert NodeName.DISPATCH.value in graph._nodes
        assert NodeName.MONITOR.value in graph._nodes
        assert NodeName.ADJUST.value in graph._nodes
        assert NodeName.EVOLVE.value in graph._nodes


# ---------------------------------------------------------------------------
# DeepAgent tests
# ---------------------------------------------------------------------------

class TestDeepAgent:
    def test_create_agent(self):
        agent = DeepAgent(name="test", role="testing")
        assert agent.name == "test"
        assert agent.role == "testing"
        assert agent.monologue is not None
        assert agent.vfs is not None
        assert agent.planner is not None
        assert agent.spawner is not None

    def test_inner_monologue(self):
        agent = DeepAgent()
        agent.monologue.observe("Test observation")
        agent.monologue.reason("Test reasoning")
        agent.monologue.plan("Test plan")
        agent.monologue.act("Test action")
        agent.monologue.reflect("Test reflection")
        assert len(agent.monologue.steps) == 5

    def test_monologue_stages(self):
        mono = InnerMonologue()
        mono.observe("obs")
        mono.reason("reason")
        mono.plan("plan")
        mono.act("act")
        mono.reflect("reflect")
        assert mono.steps[0].stage == MonologueStage.OBSERVE
        assert mono.steps[-1].stage == MonologueStage.REFLECT

    def test_vfs(self):
        vfs = VirtualFileSystem()
        vfs.write("/test.txt", "hello world")
        file = vfs.read("/test.txt")
        assert file is not None
        assert file.content == "hello world"

    def test_vfs_search(self):
        vfs = VirtualFileSystem()
        vfs.write("/a.txt", "hello world")
        vfs.write("/b.txt", "goodbye world")
        results = vfs.search("hello")
        assert len(results) == 1

    def test_planning_tool(self):
        tool = PlanningTool()
        plan = tool.create_plan("Test goal", {})
        assert len(plan.steps) == 3

    def test_plan(self):
        plan = Plan(title="Test")
        step = plan.add_step("Step 1", "Do something")
        assert len(plan.steps) == 1
        assert step.status == "pending"

    def test_plan_complete_step(self):
        plan = Plan(title="Test")
        step = plan.add_step("Step 1")
        plan.complete_step(step.id, "Done")
        assert step.status == "completed"

    def test_subagent_spawner(self):
        spawner = SubAgentSpawner()
        task = spawner.spawn("Test task", {})
        assert task.status == "pending"
        spawner.complete(task.id, "Result")
        assert spawner.get_result(task.id) == "Result"

    def test_deepagent_think(self):
        agent = DeepAgent()
        result = agent.think("Test observation")
        assert result == "Reasoning complete"

    def test_deepagent_plan(self):
        agent = DeepAgent()
        plan = agent.plan("Test goal", {})
        assert plan is not None
        assert len(plan.steps) > 0

    def test_deepagent_spawn_subagent(self):
        agent = DeepAgent()
        task_id = agent.spawn_subagent("Test sub-task", {})
        assert task_id is not None

    def test_deepagent_get_status(self):
        agent = DeepAgent()
        status = agent.get_status()
        assert "id" in status
        assert "name" in status


# ---------------------------------------------------------------------------
# Node handler tests
# ---------------------------------------------------------------------------

class TestNodeHandlers:
    def test_plan_node(self):
        state = SupervisorState(goal_description="Build a REST API")
        result = plan_node(state)
        assert result.plan is not None
        assert result.total_steps > 0

    def test_dispatch_node(self):
        state = SupervisorState(goal_description="Test")
        state.plan = {
            "steps": [{"id": "1", "title": "Step 1", "status": "pending"}],
            "total_steps": 1,
        }
        result = dispatch_node(state)
        assert len(result.results) > 0

    def test_monitor_node(self):
        state = SupervisorState(goal_description="Test")
        state.plan = {"steps": [{"id": "1", "title": "Step 1", "status": "completed"}]}
        state.total_steps = 1
        state.current_step = 1
        result = monitor_node(state)
        assert result.score > 0

    def test_adjust_node(self):
        state = SupervisorState(goal_description="Test")
        state.stall_count = 3
        result = adjust_node(state)
        assert result.stall_count == 0

    def test_evolve_node(self):
        state = SupervisorState(goal_description="Test")
        state.stall_count = 5
        result = evolve_node(state)
        assert len(result.evolution_history) > 0


# ---------------------------------------------------------------------------
# Edge predicate tests
# ---------------------------------------------------------------------------

class TestEdgePredicates:
    def test_is_completed(self):
        state = SupervisorState()
        state.score = 1.0
        assert is_completed(state)

    def test_is_not_completed(self):
        state = SupervisorState()
        state.score = 0.5
        assert not is_completed(state)

    def test_is_stalled(self):
        state = SupervisorState()
        state.stall_count = 3
        assert is_stalled(state)

    def test_has_more_steps(self):
        state = SupervisorState()
        state.current_step = 0
        state.total_steps = 5
        assert has_more_steps(state)

    def test_always_continue(self):
        state = SupervisorState()
        assert always_continue(state)


# ---------------------------------------------------------------------------
# Integrated Supervisor tests
# ---------------------------------------------------------------------------

class TestIntegratedSupervisor:
    def test_create_supervisor(self):
        supervisor = IntegratedSupervisor()
        assert supervisor is not None

    def test_run_supervisor(self):
        supervisor = IntegratedSupervisor()
        state = supervisor.run("Test goal")
        assert state is not None
        assert state.goal_status in ("completed", "failed", "timeout")

    def test_get_execution_log(self):
        supervisor = IntegratedSupervisor()
        supervisor.run("Test goal")
        log = supervisor.get_execution_log()
        assert len(log) > 0

    def test_get_world_model(self):
        supervisor = IntegratedSupervisor()
        wm = supervisor.get_world_model()
        assert wm is not None
