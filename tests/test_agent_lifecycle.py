"""Tests for the LangGraph agent lifecycle graph."""

from __future__ import annotations

import pytest

from src.harness.agent import (
    AgentState,
    build_agent_graph,
    build_cyclic_agent_graph,
    initial_state,
    validate_state,
)
from src.harness.agent.graph_builder import run_agent
from src.harness.agent.lifecycle_nodes import (
    act_node,
    list_tools,
    observe_node,
    plan_node,
    reflect_node,
    register_tool,
    verify_node,
    route_after_act,
    route_after_verify,
)
from src.harness.agent.state import AgentState as AgentState2


# ── State Tests ───────────────────────────────────────────────────────


class TestAgentState:
    def test_initial_state_creation(self):
        state = initial_state(goal="test goal", max_steps=10)
        assert state["goal"] == "test goal"
        assert state["max_steps"] == 10
        assert state["status"] == "running"
        assert state["step_count"] == 0
        assert state["current_step"] == 0
        assert state["retries"] == 0
        assert len(state["run_id"]) > 0

    def test_initial_state_default_run_id(self):
        state = initial_state(goal="test")
        assert len(state["run_id"]) == 8

    def test_initial_state_custom_run_id(self):
        state = initial_state(goal="test", run_id="custom123")
        assert state["run_id"] == "custom123"

    def test_validate_state_valid(self):
        state = initial_state(goal="test")
        errors = validate_state(state)
        assert errors == []

    def test_validate_state_empty_goal(self):
        state = initial_state(goal="")
        errors = validate_state(state)
        assert "goal must be non-empty" in errors

    def test_validate_state_negative_step_count(self):
        state = initial_state(goal="test")
        state["step_count"] = -1
        errors = validate_state(state)
        assert "step_count must be >= 0" in errors

    def test_validate_state_invalid_status(self):
        state = initial_state(goal="test")
        state["status"] = "invalid"
        errors = validate_state(state)
        assert "invalid status" in errors[0]


# ── Tool Registry Tests ───────────────────────────────────────────────


class TestToolRegistry:
    def test_list_tools(self):
        tools = list_tools()
        assert "echo" in tools
        assert "uppercase" in tools
        assert "python_exec" in tools
        assert "file_write" in tools
        assert "search" in tools

    def test_register_custom_tool(self):
        def my_tool(input_data):
            return f"custom: {input_data.get('x', '')}"

        register_tool("my_tool", my_tool, "A custom tool")
        assert "my_tool" in list_tools()

    def test_echo_tool(self):
        state = initial_state(goal="echo test")
        result = plan_node(state)
        # echo is the default fallback
        assert len(result["plan"]) > 0


# ── Node Tests ────────────────────────────────────────────────────────


class TestPlanNode:
    def test_plan_echo(self):
        state = initial_state(goal="echo hello world")
        result = plan_node(state)
        assert len(result["plan"]) > 0
        assert result["plan"][0]["tool"] == "echo"

    def test_plan_file_write(self):
        state = initial_state(goal="write file output.txt containing hello")
        result = plan_node(state)
        assert result["plan"][0]["tool"] == "file_write"
        assert result["plan"][0]["input"]["path"] == "output.txt"
        assert result["plan"][0]["input"]["content"] == "hello"

    def test_plan_computation(self):
        state = initial_state(goal="compute 2 + 2")
        result = plan_node(state)
        assert result["plan"][0]["tool"] == "python_exec"

    def test_plan_search(self):
        state = initial_state(goal="search for python tutorials")
        result = plan_node(state)
        assert result["plan"][0]["tool"] == "search"

    def test_plan_uppercase(self):
        state = initial_state(goal="uppercase hello world")
        result = plan_node(state)
        assert result["plan"][0]["tool"] == "uppercase"

    def test_plan_step_count_incremented(self):
        state = initial_state(goal="test")
        result = plan_node(state)
        assert result["step_count"] == 1


class TestActNode:
    def test_act_executes_first_step(self):
        state = initial_state(goal="echo hello")
        state = {**state, **plan_node(state)}
        result = act_node(state)
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["ok"] is True

    def test_act_advances_after_verify(self):
        state = initial_state(goal="echo hello")
        state = {**state, **plan_node(state)}
        state["verification_passed"] = True
        state["current_step"] = 0
        # Plan has 1 step, so advancing would go past end
        # Let's use a multi-step plan
        state["plan"] = [
            {"tool": "echo", "input": {"text": "step1"}, "description": "step 1"},
            {"tool": "echo", "input": {"text": "step2"}, "description": "step 2"},
        ]
        result = act_node(state)
        assert result["current_step"] == 1

    def test_act_completes_when_all_steps_done(self):
        state = initial_state(goal="echo hello")
        state = {**state, **plan_node(state)}
        state["current_step"] = 5  # past end
        result = act_node(state)
        assert result.get("status") == "completed"


class TestObserveNode:
    def test_observe_records_result(self):
        state = initial_state(goal="echo hello")
        state["tool_results"] = [
            {"tool": "echo", "input": {"text": "hello"}, "output": "hello", "ok": True, "error": ""}
        ]
        result = observe_node(state)
        assert len(result["observations"]) == 1
        assert "echo" in result["observations"][0]

    def test_observe_no_results(self):
        state = initial_state(goal="test")
        result = observe_node(state)
        assert result["observations"] == ["No tool results to observe"]


class TestReflectNode:
    def test_reflect_on_failure(self):
        state = initial_state(goal="test")
        state["tool_results"] = [
            {"tool": "unknown", "input": {}, "output": "", "ok": False, "error": "Unknown tool: unknown"}
        ]
        state["plan"] = [{"tool": "unknown", "input": {}, "description": "test"}]
        state["current_step"] = 0
        state["retries"] = 0
        result = reflect_node(state)
        assert len(result["reflections"]) == 1
        assert "failed" in result["reflections"][0].lower()
        assert result["retries"] == 1

    def test_reflect_on_success(self):
        state = initial_state(goal="test")
        state["tool_results"] = [
            {"tool": "echo", "input": {"text": "hi"}, "output": "hi", "ok": True, "error": ""}
        ]
        state["retries"] = 0
        result = reflect_node(state)
        assert "successfully" in result["reflections"][0].lower()


class TestVerifyNode:
    def test_verify_passed(self):
        state = initial_state(goal="echo hello")
        state["tool_results"] = [
            {"tool": "echo", "input": {"text": "hello"}, "output": "hello", "ok": True, "error": ""}
        ]
        state["plan"] = [{"tool": "echo", "input": {"text": "hello"}, "description": "test"}]
        state["current_step"] = 0
        result = verify_node(state)
        assert result["verification_passed"] is True

    def test_verify_failed_no_output(self):
        state = initial_state(goal="test")
        state["tool_results"] = [
            {"tool": "echo", "input": {}, "output": "", "ok": False, "error": "fail"}
        ]
        state["plan"] = [{"tool": "echo", "input": {}, "description": "test"}]
        state["current_step"] = 0
        result = verify_node(state)
        assert result["verification_passed"] is False


# ── Routing Tests ─────────────────────────────────────────────────────


class TestRouting:
    def test_route_after_act_success(self):
        state = initial_state(goal="test")
        state["tool_results"] = [
            {"tool": "echo", "input": {"text": "hi"}, "output": "hi", "ok": True, "error": ""}
        ]
        assert route_after_act(state) == "observe"

    def test_route_after_act_failure(self):
        state = initial_state(goal="test")
        state["tool_results"] = [
            {"tool": "echo", "input": {}, "output": "", "ok": False, "error": "fail"}
        ]
        assert route_after_act(state) == "reflect"

    def test_route_after_verify_done(self):
        state = initial_state(goal="test")
        state["verification_passed"] = True
        state["current_step"] = 0
        state["plan"] = [{"tool": "echo", "input": {}, "description": "only step"}]
        assert route_after_verify(state) == "__end__"

    def test_route_after_verify_more_steps(self):
        state = initial_state(goal="test")
        state["verification_passed"] = True
        state["current_step"] = 0
        state["plan"] = [
            {"tool": "echo", "input": {}, "description": "step 1"},
            {"tool": "echo", "input": {}, "description": "step 2"},
        ]
        assert route_after_verify(state) == "act"

    def test_route_after_verify_retry(self):
        state = initial_state(goal="test")
        state["verification_passed"] = False
        state["retries"] = 0
        assert route_after_verify(state) == "reflect"

    def test_route_after_verify_give_up(self):
        state = initial_state(goal="test")
        state["verification_passed"] = False
        state["retries"] = 5
        assert route_after_verify(state) == "__end__"


# ── Graph Integration Tests ───────────────────────────────────────────


class TestGraphBuilder:
    def test_build_agent_graph(self):
        graph = build_agent_graph()
        assert graph is not None

    def test_build_cyclic_agent_graph(self):
        graph = build_cyclic_agent_graph()
        assert graph is not None

    def test_run_agent_echo(self):
        result = run_agent("echo hello world")
        assert result["status"] == "completed"
        assert result["verification_passed"] is True
        assert result["step_count"] > 0

    def test_run_agent_file_write(self):
        result = run_agent("write file output.txt containing hello world")
        assert result["status"] == "completed"
        assert result["verification_passed"] is True

    def test_run_agent_computation(self):
        result = run_agent("compute 2 + 2")
        assert result["status"] == "completed"

    def test_run_agent_search(self):
        result = run_agent("search for python")
        assert result["status"] == "completed"

    def test_run_agent_default(self):
        result = run_agent("do something generic")
        assert result["status"] == "completed"

    def test_run_agent_with_custom_run_id(self):
        result = run_agent("echo test", run_id="test123")
        assert result["run_id"] == "test123"

    def test_run_agent_state_fields(self):
        result = run_agent("echo hello")
        assert "goal" in result
        assert "plan" in result
        assert "tool_results" in result
        assert "observations" in result
        assert "reflections" in result
        assert "verification_details" in result
        assert "messages" in result

    def test_cyclic_graph_runs(self):
        graph = build_cyclic_agent_graph()
        state = initial_state(goal="echo hello")
        config = {"configurable": {"thread_id": state["run_id"]}}
        result = graph.invoke(state, config=config)
        assert result["status"] == "completed"

    def test_graph_with_checkpoint(self):
        """Test that checkpointing works across multiple invocations."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = build_agent_graph(checkpointer=checkpointer)
        state = initial_state(goal="echo checkpoint test")
        config = {"configurable": {"thread_id": "checkpoint_test"}}
        result = graph.invoke(state, config=config)
        assert result["status"] == "completed"

        # Check that checkpoint was saved
        checkpoint = checkpointer.get(config)
        assert checkpoint is not None
