"""Tests for AgentKernel."""

import pytest

from agentkernel.runtime import (
    Agent,
    AgentState,
    AgentPriority,
    AgentMessage,
    AgentTask,
    AgentRuntime,
)


class TestAgent:
    def test_create(self):
        agent = Agent(name="Test Agent")
        assert agent.name == "Test Agent"
        assert agent.state == AgentState.CREATED
        assert agent.priority == AgentPriority.MEDIUM

    def test_create_task(self):
        agent = Agent(name="Test")
        task = agent.create_task("Task 1", "Description")
        assert task.name == "Task 1"
        assert len(agent.tasks) == 1

    def test_get_task(self):
        agent = Agent(name="Test")
        task = agent.create_task("Task 1")
        found = agent.get_task(task.id)
        assert found == task

    def test_get_pending_tasks(self):
        agent = Agent(name="Test")
        agent.create_task("Task 1")
        agent.create_task("Task 2")
        pending = agent.get_pending_tasks()
        assert len(pending) == 2

    def test_get_completed_tasks(self):
        agent = Agent(name="Test")
        task = agent.create_task("Task 1")
        task.status = "completed"
        completed = agent.get_completed_tasks()
        assert len(completed) == 1


class TestAgentRuntime:
    def test_create(self):
        runtime = AgentRuntime()
        assert runtime is not None

    def test_create_agent(self):
        runtime = AgentRuntime()
        agent = runtime.create_agent("Agent 1", capabilities=["read", "write"])
        assert agent.name == "Agent 1"
        assert "read" in agent.capabilities
        assert agent.id in runtime._agents

    def test_get_agent(self):
        runtime = AgentRuntime()
        agent = runtime.create_agent("Agent 1")
        found = runtime.get_agent(agent.id)
        assert found == agent

    def test_list_agents(self):
        runtime = AgentRuntime()
        runtime.create_agent("Agent 1")
        runtime.create_agent("Agent 2")
        assert len(runtime.list_agents()) == 2

    def test_list_agents_by_state(self):
        runtime = AgentRuntime()
        agent = runtime.create_agent("Agent 1")
        agent.state = AgentState.RUNNING
        runtime.create_agent("Agent 2")
        running = runtime.list_agents(state=AgentState.RUNNING)
        assert len(running) == 1

    def test_delete_agent(self):
        runtime = AgentRuntime()
        agent = runtime.create_agent("Agent 1")
        assert runtime.delete_agent(agent.id) is True
        assert runtime.get_agent(agent.id) is None

    def test_send_message(self):
        runtime = AgentRuntime()
        sender = runtime.create_agent("Sender")
        receiver = runtime.create_agent("Receiver")
        message = runtime.send_message(sender.id, receiver.id, "Hello")
        assert message is not None
        assert len(receiver.inbox) == 1
        assert len(sender.outbox) == 1

    def test_send_message_invalid_receiver(self):
        runtime = AgentRuntime()
        sender = runtime.create_agent("Sender")
        message = runtime.send_message(sender.id, "invalid", "Hello")
        assert message is None

    def test_register_message_handler(self):
        runtime = AgentRuntime()
        runtime.register_message_handler("greeting", lambda msg: None)
        assert "greeting" in runtime._message_handlers

    def test_register_task_handler(self):
        runtime = AgentRuntime()
        runtime.register_task_handler("process", lambda task: None)
        assert "process" in runtime._task_handlers

    def test_get_stats(self):
        runtime = AgentRuntime()
        runtime.create_agent("Agent 1")
        runtime.create_agent("Agent 2")
        stats = runtime.get_stats()
        assert stats["total_agents"] == 2
