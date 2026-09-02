"""Tests for AgentOS scheduler module."""

from __future__ import annotations

import pytest

from agentos.scheduler import Agent, Priority, Scheduler, ScheduleResult


class TestPriority:
    def test_priority_ordering(self) -> None:
        assert Priority.CRITICAL < Priority.HIGH < Priority.NORMAL < Priority.LOW < Priority.BACKGROUND

    def test_priority_values(self) -> None:
        assert Priority.CRITICAL == 0
        assert Priority.HIGH == 1
        assert Priority.NORMAL == 2
        assert Priority.LOW == 3
        assert Priority.BACKGROUND == 4


class TestAgent:
    def test_create_agent(self) -> None:
        agent = Agent(id="test-1", name="test")
        assert agent.id == "test-1"
        assert agent.name == "test"
        assert agent.priority == Priority.NORMAL
        assert agent.state == "pending"

    def test_agent_invalid_cpu(self) -> None:
        with pytest.raises(ValueError, match="cpu_quota must be positive"):
            Agent(id="test", name="test", cpu_quota=0)

    def test_agent_invalid_memory(self) -> None:
        with pytest.raises(ValueError, match="memory_quota must be positive"):
            Agent(id="test", name="test", memory_quota=-1)

    def test_agent_invalid_api_rate(self) -> None:
        with pytest.raises(ValueError, match="api_rate_limit must be positive"):
            Agent(id="test", name="test", api_rate_limit=0)


class TestScheduler:
    def test_create_scheduler(self) -> None:
        scheduler = Scheduler(max_concurrent=2, max_cpu=4.0, max_memory=4096)
        assert scheduler.max_concurrent == 2
        assert scheduler.queue_size == 0
        assert scheduler.running_count == 0

    def test_submit_agent(self) -> None:
        scheduler = Scheduler(max_concurrent=2)
        agent = Agent(id="a1", name="test", cpu_quota=1.0, memory_quota=256)
        result = scheduler.submit(agent)
        assert result.action == "scheduled"
        assert scheduler.running_count == 1

    def test_queue_when_full(self) -> None:
        scheduler = Scheduler(max_concurrent=1)
        a1 = Agent(id="a1", name="test1", cpu_quota=1.0, memory_quota=256)
        a2 = Agent(id="a2", name="test2", cpu_quota=1.0, memory_quota=256)
        scheduler.submit(a1)
        result = scheduler.submit(a2)
        assert result.action == "queued"
        assert scheduler.queue_size == 1

    def test_complete_agent(self) -> None:
        scheduler = Scheduler(max_concurrent=1)
        a1 = Agent(id="a1", name="test1", cpu_quota=1.0, memory_quota=256)
        scheduler.submit(a1)
        result = scheduler.complete("a1")
        assert result is not None
        assert result.action == "completed"
        assert scheduler.running_count == 0

    def test_fail_agent(self) -> None:
        scheduler = Scheduler(max_concurrent=1)
        a1 = Agent(id="a1", name="test1", cpu_quota=1.0, memory_quota=256)
        scheduler.submit(a1)
        result = scheduler.fail("a1", reason="error")
        assert result is not None
        assert result.action == "failed"

    def test_preemption(self) -> None:
        scheduler = Scheduler(max_concurrent=1)
        low = Agent(id="low", name="low", priority=Priority.LOW,
                    cpu_quota=1.0, memory_quota=256)
        high = Agent(id="high", name="high", priority=Priority.CRITICAL,
                     cpu_quota=1.0, memory_quota=256)
        scheduler.submit(low)
        assert scheduler.running_count == 1
        result = scheduler.submit(high)
        assert result.action == "scheduled"
        assert result.preempted_id == "low"

    def test_pause_running_agent(self) -> None:
        scheduler = Scheduler(max_concurrent=2)
        a1 = Agent(id="a1", name="test1", cpu_quota=1.0, memory_quota=256)
        scheduler.submit(a1)
        assert scheduler.pause("a1") is True
        assert scheduler.running_count == 0
        assert scheduler.queue_size == 1

    def test_reject_duplicate_agent(self) -> None:
        scheduler = Scheduler(max_concurrent=2)
        a1 = Agent(id="a1", name="test", cpu_quota=1.0, memory_quota=256)
        scheduler.submit(a1)
        result = scheduler.submit(a1)
        assert result.action == "rejected"

    def test_schedule_queue_on_completion(self) -> None:
        scheduler = Scheduler(max_concurrent=1)
        a1 = Agent(id="a1", name="test1", cpu_quota=1.0, memory_quota=256)
        a2 = Agent(id="a2", name="test2", cpu_quota=1.0, memory_quota=256)
        scheduler.submit(a1)
        scheduler.submit(a2)
        assert scheduler.queue_size == 1
        scheduler.complete("a1")
        assert scheduler.queue_size == 0
        assert scheduler.running_count == 1

    def test_history_recorded(self) -> None:
        scheduler = Scheduler(max_concurrent=1)
        a1 = Agent(id="a1", name="test", cpu_quota=1.0, memory_quota=256)
        scheduler.submit(a1)
        history = scheduler.get_history()
        assert len(history) >= 1
        assert history[0].agent_id == "a1"

    def test_cpu_limit_enforcement(self) -> None:
        scheduler = Scheduler(max_concurrent=4, max_cpu=2.0)
        a1 = Agent(id="a1", name="test1", cpu_quota=1.5, memory_quota=256)
        a2 = Agent(id="a2", name="test2", cpu_quota=1.5, memory_quota=256)
        scheduler.submit(a1)
        result = scheduler.submit(a2)
        assert result.action == "queued"

    def test_memory_limit_enforcement(self) -> None:
        scheduler = Scheduler(max_concurrent=4, max_memory=512)
        a1 = Agent(id="a1", name="test1", cpu_quota=0.5, memory_quota=300)
        a2 = Agent(id="a2", name="test2", cpu_quota=0.5, memory_quota=300)
        scheduler.submit(a1)
        result = scheduler.submit(a2)
        assert result.action == "queued"
