"""Tests for RuntimeKernel."""
import time

import pytest

from src.harness.runtime.kernel import RuntimeKernel, KernelState
from src.harness.runtime.agent_manager import AgentState
from src.harness.runtime.state_graph import StateGraphEngine, GraphState


class TestRuntimeKernel:
    def test_init(self):
        k = RuntimeKernel()
        assert k.state == KernelState.CREATED
        assert k.kernel_id.startswith("kernel-")

    def test_init_with_config(self):
        k = RuntimeKernel({"max_agents": 10})
        assert k.config.get("max_agents") == 10

    def test_initialize(self):
        k = RuntimeKernel()
        k.initialize()
        assert k.state == KernelState.READY

    def test_start(self):
        k = RuntimeKernel()
        k.start()
        assert k.state == KernelState.RUNNING

    def test_start_from_created(self):
        k = RuntimeKernel()
        k.start()
        assert k.state == KernelState.RUNNING

    def test_pause_resume(self):
        k = RuntimeKernel()
        k.start()
        k.pause()
        assert k.state == KernelState.PAUSED
        k.resume()
        assert k.state == KernelState.RUNNING

    def test_pause_invalid_state(self):
        k = RuntimeKernel()
        with pytest.raises(RuntimeError):
            k.pause()

    def test_resume_invalid_state(self):
        k = RuntimeKernel()
        with pytest.raises(RuntimeError):
            k.resume()

    def test_shutdown(self):
        k = RuntimeKernel()
        k.start()
        k.shutdown()
        assert k.state == KernelState.STOPPED

    def test_is_running(self):
        k = RuntimeKernel()
        k.start()
        assert k.is_running is True
        k.shutdown()
        assert k.is_running is False

    def test_uptime(self):
        k = RuntimeKernel()
        k.start()
        time.sleep(0.01)
        assert k.uptime > 0
        k.shutdown()

    def test_spawn_agent(self):
        k = RuntimeKernel()
        k.start()
        agent_id = k.spawn_agent("test", task="do something")
        agent = k.agents.get(agent_id)
        assert agent is not None
        assert agent.name == "test"
        assert agent.task == "do something"

    def test_start_agent(self):
        k = RuntimeKernel()
        k.start()
        agent_id = k.spawn_agent("test")
        assert k.start_agent(agent_id) is True
        assert k.agents.get(agent_id).state == AgentState.RUNNING

    def test_start_agent_invalid_state(self):
        k = RuntimeKernel()
        k.start()
        agent_id = k.spawn_agent("test")
        k.complete_agent(agent_id)
        assert k.start_agent(agent_id) is False

    def test_complete_agent(self):
        k = RuntimeKernel()
        k.start()
        agent_id = k.spawn_agent("test")
        k.start_agent(agent_id)
        assert k.complete_agent(agent_id, result="done") is True
        assert k.agents.get(agent_id).state == AgentState.COMPLETED
        assert k.agents.get(agent_id).result == "done"

    def test_fail_agent(self):
        k = RuntimeKernel()
        k.start()
        agent_id = k.spawn_agent("test")
        k.start_agent(agent_id)
        assert k.fail_agent(agent_id, "error msg") is True
        assert k.agents.get(agent_id).state == AgentState.FAILED
        assert k.agents.get(agent_id).error == "error msg"

    def test_terminate_agent(self):
        k = RuntimeKernel()
        k.start()
        agent_id = k.spawn_agent("test")
        assert k.terminate_agent(agent_id) is True
        assert k.agents.get(agent_id).state == AgentState.TERMINATED

    def test_delegate_task(self):
        k = RuntimeKernel()
        k.start()
        a1 = k.spawn_agent("sender")
        a2 = k.spawn_agent("receiver")
        k.start_agent(a1)
        k.start_agent(a2)
        assert k.delegate_task(a1, a2, "new task") is True
        assert k.agents.get(a2).task == "new task"

    def test_create_graph(self):
        k = RuntimeKernel()
        k.start()
        graph = k.create_graph("test-graph")
        assert isinstance(graph, StateGraphEngine)
        assert graph.name == "test-graph"

    def test_get_graph(self):
        k = RuntimeKernel()
        k.start()
        graph = k.create_graph("test-graph")
        graph_id = [gid for gid in k._graphs if k._graphs[gid] == graph][0]
        fetched = k.get_graph(graph_id)
        assert fetched is graph

    def test_get_graph_missing(self):
        k = RuntimeKernel()
        assert k.get_graph("nonexistent") is None

    def test_execute_graph(self):
        k = RuntimeKernel()
        k.start()
        graph = k.create_graph("test")
        graph.add_node("n1", lambda s: s)
        graph.set_entry_point("n1")
        result = k.execute_graph(graph)
        assert result.success is True

    def test_execute_graph_by_id(self):
        k = RuntimeKernel()
        k.start()
        graph = k.create_graph("test")
        graph.add_node("n1", lambda s: s)
        graph.set_entry_point("n1")
        graph_id = [gid for gid in k._graphs if k._graphs[gid] == graph][0]
        result = k.execute_graph(graph_id)
        assert result.success is True

    def test_execute_graph_missing(self):
        k = RuntimeKernel()
        k.start()
        with pytest.raises(ValueError):
            k.execute_graph("nonexistent")

    def test_get_status(self):
        k = RuntimeKernel()
        k.start()
        status = k.get_status()
        assert "kernel_id" in status
        assert status["state"] == "running"
        assert "agents" in status

    def test_on_event_decorator(self):
        k = RuntimeKernel()
        k.start()
        results = []
        @k.on_event("test.event")
        def handler(e):
            results.append(e.data)
        k.emit_event("test.event", "data")
        assert results == ["data"]

    def test_emit_event(self):
        k = RuntimeKernel()
        k.start()
        event = k.emit_event("test", {"key": "value"})
        assert event.name == "test"
        assert event.data == {"key": "value"}

    def test_publish_message(self):
        k = RuntimeKernel()
        k.start()
        results = []
        k.subscribe_topic("test", lambda msg: results.append(msg.data))
        k.publish_message("test", data="msg")
        assert results == ["msg"]

    def test_subscribe_topic(self):
        k = RuntimeKernel()
        k.start()
        results = []
        @k.subscribe_topic("test")
        def handler(msg):
            results.append(msg.data)
        k.publish_message("test", data="msg")
        assert results == ["msg"]

    def test_shutdown_terminates_agents(self):
        k = RuntimeKernel()
        k.start()
        a1 = k.spawn_agent("test1")
        k.start_agent(a1)
        a2 = k.spawn_agent("test2")
        k.start_agent(a2)
        k.shutdown()
        assert k.agents.get(a1).state == AgentState.TERMINATED
        assert k.agents.get(a2).state == AgentState.TERMINATED

    def test_events_fired_on_lifecycle(self):
        k = RuntimeKernel()
        events = []
        k.events.on("kernel.initialized", lambda e: events.append(e.name))
        k.events.on("kernel.started", lambda e: events.append(e.name))
        k.start()
        assert "kernel.initialized" in events
        assert "kernel.started" in events

    def test_events_fired_on_agent_spawn(self):
        k = RuntimeKernel()
        k.start()
        events = []
        k.events.on("agent.spawned", lambda e: events.append(e.data))
        k.spawn_agent("test")
        assert len(events) == 1
        assert events[0]["name"] == "test"

    def test_config_change_event(self):
        k = RuntimeKernel()
        k.start()
        events = []
        k.events.on("config.changed", lambda e: events.append(e.data))
        k.config.set("new_key", "new_value")
        assert len(events) == 1
        assert events[0]["key"] == "new_key"

    def test_full_workflow(self):
        k = RuntimeKernel()
        k.start()

        # Create and execute a graph
        graph = k.create_graph("workflow")
        graph.add_node("step1", lambda s: s)
        graph.add_node("step2", lambda s: s)
        graph.add_edge("step1", "step2")
        graph.set_entry_point("step1")
        result = k.execute_graph(graph)
        assert result.success is True

        # Spawn and manage agents
        a1 = k.spawn_agent("worker", task="process")
        k.start_agent(a1)
        k.complete_agent(a1, result="done")

        status = k.get_status()
        assert status["agents"]["completed"] == 1

        k.shutdown()
        assert k.state == KernelState.STOPPED
