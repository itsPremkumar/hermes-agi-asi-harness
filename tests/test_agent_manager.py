"""Tests for AgentManager."""
import time

import pytest

from src.harness.runtime.agent_manager import AgentManager, AgentState, AgentInfo


class TestAgentManager:
    def test_init(self):
        am = AgentManager()
        assert len(am.get_all()) == 0

    def test_spawn(self):
        am = AgentManager()
        agent = am.spawn("test-agent", agent_type="worker")
        assert agent.name == "test-agent"
        assert agent.agent_type == "worker"
        assert agent.state == AgentState.PENDING
        assert agent.agent_id.startswith("agent-")

    def test_spawn_with_custom_id(self):
        am = AgentManager()
        agent = am.spawn("test", agent_id="custom-123")
        assert agent.agent_id == "custom-123"

    def test_spawn_duplicate_id_raises(self):
        am = AgentManager()
        am.spawn("test", agent_id="dup")
        with pytest.raises(ValueError):
            am.spawn("test2", agent_id="dup")

    def test_spawn_with_parent(self):
        am = AgentManager()
        parent = am.spawn("parent")
        child = am.spawn("child", parent_id=parent.agent_id)
        assert child.parent_id == parent.agent_id
        assert parent.agent_id in child.parent_id

    def test_get(self):
        am = AgentManager()
        agent = am.spawn("test")
        fetched = am.get(agent.agent_id)
        assert fetched is not None
        assert fetched.agent_id == agent.agent_id

    def test_get_missing(self):
        am = AgentManager()
        assert am.get("nonexistent") is None

    def test_get_all(self):
        am = AgentManager()
        am.spawn("a1")
        am.spawn("a2")
        assert len(am.get_all()) == 2

    def test_get_by_type(self):
        am = AgentManager()
        am.spawn("w1", agent_type="worker")
        am.spawn("w2", agent_type="worker")
        am.spawn("m1", agent_type="manager")
        workers = am.get_by_type("worker")
        assert len(workers) == 2

    def test_get_by_state(self):
        am = AgentManager()
        a1 = am.spawn("a1")
        a2 = am.spawn("a2")
        am.transition(a1.agent_id, AgentState.RUNNING)
        running = am.get_by_state(AgentState.RUNNING)
        assert len(running) == 1
        assert running[0].agent_id == a1.agent_id

    def test_get_children(self):
        am = AgentManager()
        parent = am.spawn("parent")
        child1 = am.spawn("child1", parent_id=parent.agent_id)
        child2 = am.spawn("child2", parent_id=parent.agent_id)
        children = am.get_children(parent.agent_id)
        assert len(children) == 2

    def test_get_root_agents(self):
        am = AgentManager()
        parent = am.spawn("parent")
        am.spawn("child", parent_id=parent.agent_id)
        roots = am.get_root_agents()
        assert len(roots) == 1
        assert roots[0].agent_id == parent.agent_id

    def test_transition(self):
        am = AgentManager()
        agent = am.spawn("test")
        assert am.transition(agent.agent_id, AgentState.RUNNING) is True
        assert am.get(agent.agent_id).state == AgentState.RUNNING

    def test_transition_sets_started_at(self):
        am = AgentManager()
        agent = am.spawn("test")
        am.transition(agent.agent_id, AgentState.RUNNING)
        assert am.get(agent.agent_id).started_at is not None

    def test_transition_sets_ended_at(self):
        am = AgentManager()
        agent = am.spawn("test")
        am.transition(agent.agent_id, AgentState.RUNNING)
        am.transition(agent.agent_id, AgentState.COMPLETED)
        assert am.get(agent.agent_id).ended_at is not None

    def test_transition_with_error(self):
        am = AgentManager()
        agent = am.spawn("test")
        am.transition(agent.agent_id, AgentState.FAILED, error="something broke")
        assert am.get(agent.agent_id).error == "something broke"

    def test_transition_with_result(self):
        am = AgentManager()
        agent = am.spawn("test")
        am.transition(agent.agent_id, AgentState.COMPLETED, result={"data": 42})
        assert am.get(agent.agent_id).result == {"data": 42}

    def test_transition_missing_agent(self):
        am = AgentManager()
        assert am.transition("nonexistent", AgentState.RUNNING) is False

    def test_delegate(self):
        am = AgentManager()
        a1 = am.spawn("sender")
        a2 = am.spawn("receiver")
        assert am.delegate(a1.agent_id, a2.agent_id, "do this") is True
        assert am.get(a2.agent_id).task == "do this"
        assert am.get(a2.agent_id).state == AgentState.RUNNING

    def test_delegate_missing_agent(self):
        am = AgentManager()
        a1 = am.spawn("sender")
        assert am.delegate(a1.agent_id, "missing", "task") is False

    def test_terminate(self):
        am = AgentManager()
        agent = am.spawn("test")
        assert am.terminate(agent.agent_id) is True
        assert am.get(agent.agent_id).state == AgentState.TERMINATED

    def test_terminate_recursive(self):
        am = AgentManager()
        parent = am.spawn("parent")
        child = am.spawn("child", parent_id=parent.agent_id)
        am.terminate(parent.agent_id, recursive=True)
        assert am.get(parent.agent_id).state == AgentState.TERMINATED
        assert am.get(child.agent_id).state == AgentState.TERMINATED

    def test_terminate_missing(self):
        am = AgentManager()
        assert am.terminate("nonexistent") is False

    def test_set_result(self):
        am = AgentManager()
        agent = am.spawn("test")
        assert am.set_result(agent.agent_id, "done") is True
        assert am.get(agent.agent_id).result == "done"

    def test_set_result_missing(self):
        am = AgentManager()
        assert am.set_result("nonexistent", "x") is False

    def test_set_on_complete(self):
        am = AgentManager()
        agent = am.spawn("test")
        results = []
        assert am.set_on_complete(agent.agent_id, lambda a: results.append(a.agent_id)) is True
        am.transition(agent.agent_id, AgentState.COMPLETED)
        assert results == [agent.agent_id]

    def test_set_on_complete_missing(self):
        am = AgentManager()
        assert am.set_on_complete("nonexistent", lambda a: None) is False

    def test_get_active_count(self):
        am = AgentManager()
        a1 = am.spawn("a1")
        a2 = am.spawn("a2")
        am.transition(a1.agent_id, AgentState.RUNNING)
        am.transition(a2.agent_id, AgentState.COMPLETED)
        assert am.get_active_count() == 1

    def test_get_stats(self):
        am = AgentManager()
        a1 = am.spawn("a1")
        a2 = am.spawn("a2")
        am.transition(a1.agent_id, AgentState.RUNNING)
        stats = am.get_stats()
        assert stats["running"] == 1
        assert stats["pending"] == 1

    def test_remove(self):
        am = AgentManager()
        agent = am.spawn("test")
        assert am.remove(agent.agent_id) is True
        assert am.get(agent.agent_id) is None

    def test_remove_missing(self):
        am = AgentManager()
        assert am.remove("nonexistent") is False

    def test_clear(self):
        am = AgentManager()
        am.spawn("a1")
        am.spawn("a2")
        am.clear()
        assert len(am.get_all()) == 0

    def test_agent_info_duration(self):
        am = AgentManager()
        agent = am.spawn("test")
        am.transition(agent.agent_id, AgentState.RUNNING)
        time.sleep(0.01)
        am.transition(agent.agent_id, AgentState.COMPLETED)
        duration = am.get(agent.agent_id).duration
        assert duration is not None
        assert duration > 0

    def test_agent_info_is_active(self):
        am = AgentManager()
        agent = am.spawn("test")
        am.transition(agent.agent_id, AgentState.RUNNING)
        assert am.get(agent.agent_id).is_active is True

    def test_agent_info_is_terminal(self):
        am = AgentManager()
        agent = am.spawn("test")
        am.transition(agent.agent_id, AgentState.COMPLETED)
        assert am.get(agent.agent_id).is_terminal is True

    def test_parent_child_relationship(self):
        am = AgentManager()
        parent = am.spawn("parent")
        child = am.spawn("child", parent_id=parent.agent_id)
        assert child.agent_id in am.get(parent.agent_id).children_ids

    def test_remove_updates_parent(self):
        am = AgentManager()
        parent = am.spawn("parent")
        child = am.spawn("child", parent_id=parent.agent_id)
        am.remove(child.agent_id)
        assert child.agent_id not in am.get(parent.agent_id).children_ids
