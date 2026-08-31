"""Tests for Harness Runtime Kernel — LangGraph StateGraph + Agent Lifecycle."""
import os
import sys

# Ensure THIS workspace is first on sys.path
workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace in sys.path:
    sys.path.remove(workspace)
sys.path.insert(0, workspace)

import pytest
from harnix.state import AgentState, AgentPhase, create_initial_state
from harnix.nodes import (
    init_node, plan_node, dispatch_node, monitor_node,
    adjust_node, evolve_node, complete_node,
    route_after_monitor, route_after_adjust, route_after_evolve,
)
from harnix.kernel import HarnessRuntimeKernel


class TestAgentState:
    """Test AgentState creation and defaults."""

    def test_create_initial_state(self):
        state = create_initial_state("test task")
        assert state["task_description"] == "test task"
        assert state["phase"] == AgentPhase.INIT
        assert state["status"] == "running"
        assert state["iteration"] == 0
        assert state["max_iterations"] == 20
        assert state["max_stalls"] == 5
        assert state["score"] == 0.0
        assert state["stall_count"] == 0
        assert state["plan"] == []
        assert state["results"] == []
        assert state["errors"] == []

    def test_create_initial_state_custom(self):
        state = create_initial_state("task", max_iterations=50, max_stalls=10, context={"key": "val"})
        assert state["max_iterations"] == 50
        assert state["max_stalls"] == 10
        assert state["context"] == {"key": "val"}

    def test_agent_id_generated(self):
        state = create_initial_state("task")
        assert state["agent_id"].startswith("agent-")
        assert state["run_id"].startswith("run-")


class TestNodes:
    """Test individual LangGraph nodes."""

    def test_init_node(self):
        state = create_initial_state("test task")
        result = init_node(state)
        assert result["phase"] == AgentPhase.PLANNING
        assert result["iteration"] == 1
        assert len(result["messages"]) == 1
        assert "test task" in result["messages"][0]

    def test_plan_node_file_task(self):
        state = create_initial_state("write file demo.txt containing HELLO")
        state = init_node(state)
        result = plan_node(state)
        assert result["phase"] == AgentPhase.PLANNING
        assert result["total_steps"] == 1
        assert result["plan"][0]["action"] == "write_file"

    def test_plan_node_compute_task(self):
        state = create_initial_state("compute 2 + 2")
        state = init_node(state)
        result = plan_node(state)
        assert result["total_steps"] == 1
        assert result["plan"][0]["action"] == "compute"

    def test_plan_node_fetch_task(self):
        state = create_initial_state("fetch https://example.com")
        state = init_node(state)
        result = plan_node(state)
        assert result["total_steps"] == 1
        assert result["plan"][0]["action"] == "fetch"

    def test_dispatch_node(self):
        state = create_initial_state("compute 2 + 2")
        state = init_node(state)
        state = plan_node(state)
        result = dispatch_node(state)
        assert result["phase"] == AgentPhase.DISPATCHING
        assert result["current_step"] == 1
        assert len(result["results"]) == 1

    def test_monitor_node_completes(self):
        state = create_initial_state("compute 2 + 2")
        state = init_node(state)
        state = plan_node(state)
        state = dispatch_node(state)
        result = monitor_node(state)
        # When all steps are done, monitor transitions to COMPLETING
        assert result["phase"] == AgentPhase.COMPLETING
        assert result["score"] == 1.0
        assert result["status"] == "completed"

    def test_complete_node(self):
        state = create_initial_state("task")
        result = complete_node(state)
        assert result["phase"] == AgentPhase.COMPLETED
        assert result["status"] == "completed"

    def test_adjust_node(self):
        state = create_initial_state("task")
        state["stall_count"] = 3
        result = adjust_node(state)
        assert result["phase"] == AgentPhase.ADJUSTING
        assert result["stall_count"] == 0
        assert result["strategy"] != "default"

    def test_evolve_node(self):
        state = create_initial_state("task")
        state["stall_count"] = 10
        result = evolve_node(state)
        assert result["phase"] == AgentPhase.EVOLVING
        assert result["stall_count"] == 0
        assert len(result["evolution_history"]) == 1


class TestEdgeRouting:
    """Test conditional edge routing logic."""

    def test_route_after_monitor_complete(self):
        state = create_initial_state("task")
        state["status"] = "completed"
        state["current_step"] = 1
        state["total_steps"] = 1
        assert route_after_monitor(state) == "complete"

    def test_route_after_monitor_evolve(self):
        state = create_initial_state("task", max_stalls=3)
        state["stall_count"] = 5
        state["current_step"] = 0
        state["total_steps"] = 1
        assert route_after_monitor(state) == "evolve"

    def test_route_after_monitor_adjust(self):
        state = create_initial_state("task")
        state["stall_count"] = 2
        state["current_step"] = 0
        state["total_steps"] = 1
        assert route_after_monitor(state) == "adjust"

    def test_route_after_monitor_dispatch(self):
        state = create_initial_state("task")
        state["stall_count"] = 0
        state["current_step"] = 0
        state["total_steps"] = 2
        assert route_after_monitor(state) == "dispatch"

    def test_route_after_adjust(self):
        state = create_initial_state("task")
        assert route_after_adjust(state) == "dispatch"

    def test_route_after_evolve(self):
        state = create_initial_state("task")
        assert route_after_evolve(state) == "dispatch"


class TestHarnessRuntimeKernel:
    """Integration tests for the full kernel."""

    def test_build(self):
        kernel = HarnessRuntimeKernel()
        result = kernel.build()
        assert result is kernel
        assert kernel._app is not None

    def test_run_file_task(self):
        kernel = HarnessRuntimeKernel()
        result = kernel.run("write file /tmp/harnix_test.txt containing HELLO")
        assert result["status"] == "completed"
        assert result["score"] == 1.0
        assert result["current_step"] == 1

    def test_run_compute_task(self):
        kernel = HarnessRuntimeKernel()
        result = kernel.run("compute 2 + 2")
        assert result["status"] == "completed"
        assert result["score"] == 1.0

    def test_run_fetch_task(self):
        kernel = HarnessRuntimeKernel()
        result = kernel.run("fetch https://example.com")
        assert result["status"] == "completed"
        assert result["score"] == 1.0

    def test_run_generic_task(self):
        kernel = HarnessRuntimeKernel()
        result = kernel.run("do something generic")
        assert result["status"] == "completed"
        assert result["score"] == 1.0

    def test_run_produces_messages(self):
        kernel = HarnessRuntimeKernel()
        result = kernel.run("compute 5 * 5")
        assert len(result["messages"]) >= 3
        assert any("[init]" in m for m in result["messages"])
        assert any("[plan]" in m for m in result["messages"])

    def test_run_produces_memory(self):
        kernel = HarnessRuntimeKernel()
        result = kernel.run("remember that Python is great")
        assert len(result["memory"]) >= 1

    def test_run_with_custom_params(self):
        kernel = HarnessRuntimeKernel(max_iterations=10, max_stalls=3)
        result = kernel.run("compute 1 + 1")
        assert result["max_iterations"] == 10
        assert result["max_stalls"] == 3

    def test_get_graph(self):
        kernel = HarnessRuntimeKernel()
        graph = kernel.get_graph()
        assert graph is not None


class TestAgentLifecycle:
    """Test the full agent lifecycle phases."""

    def test_lifecycle_phases(self):
        state = create_initial_state("test")
        assert state["phase"] == AgentPhase.INIT

        state = init_node(state)
        assert state["phase"] == AgentPhase.PLANNING

        state = plan_node(state)
        assert state["phase"] == AgentPhase.PLANNING

        state = dispatch_node(state)
        assert state["phase"] == AgentPhase.DISPATCHING

        state = monitor_node(state)
        # For a single-step task, monitor transitions to COMPLETING
        assert state["phase"] == AgentPhase.COMPLETING

    def test_stall_detection(self):
        state = create_initial_state("task")
        state = init_node(state)
        state = plan_node(state)

        # Simulate multiple iterations without progress
        for _ in range(3):
            state = monitor_node(state)

        # Stall count should increase
        assert state["stall_count"] >= 1

    def test_iteration_counter(self):
        state = create_initial_state("task")
        assert state["iteration"] == 0

        state = init_node(state)
        assert state["iteration"] == 1

        state = plan_node(state)
        assert state["iteration"] == 2

        state = dispatch_node(state)
        assert state["iteration"] == 3

        state = monitor_node(state)
        assert state["iteration"] == 4
