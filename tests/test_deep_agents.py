"""Tests for deep_agents/ — Deep Agents Coordination."""

from __future__ import annotations

import pytest

from harness.deep_agents import (
    Agent,
    AgentRole,
    AgentStatus,
    AgentTask,
    ConsensusBuilder,
    CrewOrchestrator,
    DelegationPattern,
    SubAgentSpawner,
    Team,
)
from harness.errors import DeepAgentError


class TestAgent:
    """Tests for Agent."""

    def test_create_agent(self):
        agent = Agent(name="test", role=AgentRole.EXECUTOR)
        assert agent.name == "test"
        assert agent.status == AgentStatus.IDLE

    def test_agent_can_handle(self):
        agent = Agent(name="test")
        assert agent.can_handle("any task") is True

    def test_agent_has_id(self):
        agent = Agent(name="test")
        assert agent.agent_id is not None


class TestAgentTask:
    """Tests for AgentTask."""

    def test_create_task(self):
        task = AgentTask(description="do something")
        assert task.description == "do something"
        assert task.status == "pending"

    def test_task_has_id(self):
        task = AgentTask()
        assert task.task_id is not None


class TestTeam:
    """Tests for Team."""

    def test_create_team(self):
        team = Team(name="crew")
        assert team.name == "crew"
        assert team.size == 0

    def test_add_agent(self):
        team = Team()
        agent = Agent(name="a1")
        team.add_agent(agent)
        assert team.size == 1

    def test_remove_agent(self):
        team = Team()
        agent = Agent(name="a1")
        team.add_agent(agent)
        removed = team.remove_agent(agent.agent_id)
        assert removed is not None
        assert team.size == 0

    def test_get_by_role(self):
        team = Team()
        team.add_agent(Agent(name="p1", role=AgentRole.PLANNER))
        team.add_agent(Agent(name="e1", role=AgentRole.EXECUTOR))
        planners = team.get_by_role(AgentRole.PLANNER)
        assert len(planners) == 1

    def test_get_available(self):
        team = Team()
        team.add_agent(Agent(name="a1", status=AgentStatus.IDLE))
        team.add_agent(Agent(name="a2", status=AgentStatus.WORKING))
        available = team.get_available()
        assert len(available) == 1


class TestSubAgentSpawner:
    """Tests for SubAgentSpawner."""

    def test_spawn(self):
        spawner = SubAgentSpawner()
        agent = spawner.spawn("sub1", AgentRole.EXECUTOR)
        assert agent.name == "sub1"
        assert agent.status == AgentStatus.IDLE

    def test_terminate(self):
        spawner = SubAgentSpawner()
        agent = spawner.spawn("sub1", AgentRole.EXECUTOR)
        assert spawner.terminate(agent.agent_id) is True
        assert spawner.active_count == 0

    def test_get_active(self):
        spawner = SubAgentSpawner()
        spawner.spawn("sub1", AgentRole.EXECUTOR)
        spawner.spawn("sub2", AgentRole.REVIEWER)
        assert len(spawner.get_active()) == 2

    def test_active_count(self):
        spawner = SubAgentSpawner()
        spawner.spawn("sub1", AgentRole.EXECUTOR)
        assert spawner.active_count == 1


class TestConsensusBuilder:
    """Tests for ConsensusBuilder."""

    def test_vote(self):
        cb = ConsensusBuilder(min_agreement=0.5)
        agents = [Agent(name=f"a{i}") for i in range(5)]
        result = cb.vote(agents, ["option_a", "option_b"])
        assert "votes" in result
        assert "winner" in result

    def test_consensus_reached(self):
        cb = ConsensusBuilder(min_agreement=0.3)
        agents = [Agent(name=f"a{i}") for i in range(10)]
        result = cb.vote(agents, ["x", "y", "z"])
        assert isinstance(result["consensus"], bool)

    def test_multi_round_vote(self):
        cb = ConsensusBuilder(min_agreement=0.5)
        agents = [Agent(name=f"a{i}") for i in range(5)]
        result = cb.multi_round_vote(agents, ["a", "b"], max_rounds=3)
        assert "rounds" in result

    def test_empty_agents(self):
        cb = ConsensusBuilder()
        result = cb.vote([], ["a", "b"])
        assert result["consensus"] is False


class TestCrewOrchestrator:
    """Tests for CrewOrchestrator."""

    def test_create_orchestrator(self):
        team = Team()
        orch = CrewOrchestrator(team)
        assert orch.team == team

    def test_delegate_sequential(self):
        team = Team()
        team.add_agent(Agent(name="a1", status=AgentStatus.IDLE))
        orch = CrewOrchestrator(team)
        task = AgentTask(description="test")
        delegation = orch.delegate(task, DelegationPattern.SEQUENTIAL)
        assert len(delegation.assigned_agents) >= 1

    def test_delegate_no_agents(self):
        team = Team()
        orch = CrewOrchestrator(team)
        task = AgentTask()
        with pytest.raises(DeepAgentError):
            orch.delegate(task)

    def test_execute_sequential(self):
        team = Team()
        team.add_agent(Agent(name="a1", status=AgentStatus.IDLE))
        team.add_agent(Agent(name="a2", status=AgentStatus.IDLE))
        orch = CrewOrchestrator(team)
        tasks = [AgentTask(description="t1"), AgentTask(description="t2")]
        results = orch.execute_sequential(tasks)
        assert len(results) == 2

    def test_execute_parallel(self):
        team = Team()
        team.add_agent(Agent(name="a1", status=AgentStatus.IDLE))
        team.add_agent(Agent(name="a2", status=AgentStatus.IDLE))
        orch = CrewOrchestrator(team)
        tasks = [AgentTask(description="t1"), AgentTask(description="t2")]
        results = orch.execute_parallel(tasks)
        assert len(results) == 2
