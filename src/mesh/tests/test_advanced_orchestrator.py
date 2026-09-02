"""Tests for Advanced Multi-Agent Orchestrator."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from mesh.advanced_orchestrator import (
    MultiAgentOrchestrator,
    AgentInfo,
    AgentTask,
    AgentStatus,
    TaskPriority,
    ConsensusResult,
)


class TestAgentInfo:
    def test_create(self):
        agent = AgentInfo("a1", "Agent 1", ["coding", "testing"])
        assert agent.agent_id == "a1"
        assert agent.status == AgentStatus.IDLE

    def test_create_with_metadata(self):
        agent = AgentInfo("a1", "Agent 1", [], metadata={"model": "gpt-4"})
        assert agent.metadata["model"] == "gpt-4"


class TestAgentTask:
    def test_create(self):
        task = AgentTask("t1", "Do something")
        assert task.task_id == "t1"
        assert task.status == "pending"

    def test_create_with_priority(self):
        task = AgentTask("t1", "Do something", priority=TaskPriority.HIGH)
        assert task.priority == TaskPriority.HIGH


class TestMultiAgentOrchestrator:
    def test_create(self):
        orch = MultiAgentOrchestrator()
        assert orch is not None

    def test_register_agent(self):
        orch = MultiAgentOrchestrator()
        agent = AgentInfo("a1", "Agent 1", ["coding"])
        orch.register_agent(agent)
        assert orch.get_agent_status("a1") is not None

    def test_unregister_agent(self):
        orch = MultiAgentOrchestrator()
        agent = AgentInfo("a1", "Agent 1", ["coding"])
        orch.register_agent(agent)
        orch.unregister_agent("a1")
        assert orch.get_agent_status("a1") is None

    def test_submit_task(self):
        orch = MultiAgentOrchestrator()
        task = AgentTask("t1", "Do something")
        orch.submit_task(task)
        assert len(orch.get_pending_tasks()) == 1

    def test_assign_task(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", ["coding"]))
        orch.submit_task(AgentTask("t1", "Do something"))
        assert orch.assign_task("t1", "a1") is True

    def test_assign_task_agent_not_found(self):
        orch = MultiAgentOrchestrator()
        orch.submit_task(AgentTask("t1", "Do something"))
        assert orch.assign_task("t1", "nonexistent") is False

    def test_assign_task_agent_busy(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", []))
        orch.submit_task(AgentTask("t1", "Do something"))
        orch.submit_task(AgentTask("t2", "Do something else"))
        orch.assign_task("t1", "a1")
        assert orch.assign_task("t2", "a1") is False

    def test_auto_assign(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", []))
        orch.register_agent(AgentInfo("a2", "Agent 2", []))
        orch.submit_task(AgentTask("t1", "Task 1"))
        orch.submit_task(AgentTask("t2", "Task 2"))
        assignments = orch.auto_assign()
        assert len(assignments) == 2

    def test_complete_task(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", []))
        orch.submit_task(AgentTask("t1", "Do something"))
        orch.assign_task("t1", "a1")
        orch.complete_task("t1", "result", success=True)
        assert len(orch.get_completed_tasks()) == 1

    def test_complete_task_failure(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", []))
        orch.submit_task(AgentTask("t1", "Do something", max_retries=2))
        orch.assign_task("t1", "a1")
        orch.complete_task("t1", None, success=False)
        # Should be pending again (retry)
        assert len(orch.get_pending_tasks()) == 1

    def test_complete_task_max_retries(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", []))
        orch.submit_task(AgentTask("t1", "Do something", max_retries=1))
        orch.assign_task("t1", "a1")
        orch.complete_task("t1", None, success=False)
        orch.assign_task("t1", "a1")
        orch.complete_task("t1", None, success=False)
        assert len(orch.get_pending_tasks()) == 0

    def test_reach_consensus(self):
        orch = MultiAgentOrchestrator()
        orch.submit_task(AgentTask("t1", "Task 1"))
        result = orch.reach_consensus("t1", {"a1": "option1", "a2": "option1", "a3": "option2"})
        assert isinstance(result, ConsensusResult)
        assert result.agreed is True
        assert result.result == "option1"

    def test_reach_consensus_no_agreement(self):
        orch = MultiAgentOrchestrator()
        result = orch.reach_consensus("t1", {"a1": "option1", "a2": "option2", "a3": "option3"})
        assert result.agreed is False

    def test_heartbeat(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", []))
        before = orch.get_agent_status("a1").last_heartbeat
        import time
        time.sleep(0.01)
        orch.heartbeat("a1")
        after = orch.get_agent_status("a1").last_heartbeat
        assert after > before

    def test_get_all_agents(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", []))
        orch.register_agent(AgentInfo("a2", "Agent 2", []))
        assert len(orch.get_all_agents()) == 2

    def test_get_stats(self):
        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentInfo("a1", "Agent 1", []))
        orch.submit_task(AgentTask("t1", "Task 1"))
        stats = orch.get_stats()
        assert stats["total_agents"] == 1
        assert stats["total_tasks"] == 1
