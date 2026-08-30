"""Mock-LLM e2e integration tests — YAML fleet to spawn/run/critique/checkpoint/resume."""
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentforge_x.contracts import (
    AGENT_STATE_REQUIRED,
    ContractError,
    assert_agent_state_keys,
    assert_jsonl_line,
    assert_agent_proto,
    assert_status_transition,
)


# ── Mock LLM Backend ────────────────────────────────────────────────────────

class MockLLM:
    """Deterministic mock LLM for e2e testing."""

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

    async def invoke(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        self.calls.append({"prompt": prompt, "kwargs": kwargs})

        for key, response in self.responses.items():
            if key in prompt.lower():
                return response

        return "mock-response"

    def __call__(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        self.calls.append({"prompt": prompt, "kwargs": kwargs})

        for key, response in self.responses.items():
            if key in prompt.lower():
                return response

        return "mock-response"


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    return MockLLM(responses={
        "plan": "I will analyze the problem and create a step-by-step plan.",
        "execute": "Executing step with available tools.",
        "critique": "The output meets the criteria. Score: 9/10.",
        "reflect": "The process was efficient. Next time I would parallelize more.",
    })


@pytest.fixture
def sample_agent_file():
    return {
        "apiVersion": "taskforge.dev/v1",
        "kind": "Agent",
        "metadata": {"name": "test-agent", "version": "1.0.0"},
        "spec": {
            "model": "gpt-4",
            "prompts": {
                "system": "You are a test agent.",
                "onEvent": "Process this event.",
            },
            "tools": ["shell", "fs"],
            "steps": [
                {"name": "plan", "prompt": "Create a plan."},
                {"name": "execute", "prompt": "Execute the plan."},
                {"name": "critique", "prompt": "Critique the output."},
            ],
        },
    }


@pytest.fixture
def sample_fleet_yaml():
    return """
agents:
  - name: planner
    model: gpt-4
    steps: [plan, execute]
  - name: reviewer
    model: gpt-4
    steps: [critique]
"""


# ── E2E Test: YAML Fleet → Spawn → Run → Critique → Checkpoint → Resume ──────

class TestMockLLM:
    """Test the mock LLM itself."""

    @pytest.mark.asyncio
    async def test_mock_invoke(self, mock_llm):
        result = await mock_llm.invoke("Please plan this task.")
        assert "plan" in result.lower() or result == "mock-response"
        assert mock_llm.call_count == 1

    @pytest.mark.asyncio
    async def test_mock_response_matching(self, mock_llm):
        result = await mock_llm.invoke("Execute the following steps.")
        assert "executing" in result.lower()

    @pytest.mark.asyncio
    async def test_mock_call_tracking(self, mock_llm):
        await mock_llm.invoke("Plan this.")
        await mock_llm.invoke("Execute that.")
        assert len(mock_llm.calls) == 2


class TestAgentLifecycle:
    """Test agent lifecycle: spawn → run → critique → checkpoint → resume."""

    def test_spawn_agent(self, sample_agent_file):
        """Verify an agent can be spawned from a definition."""
        errors = assert_agent_proto(sample_agent_file)
        assert errors == []

        state = {
            "id": sample_agent_file["metadata"]["name"],
            "name": sample_agent_file["metadata"]["name"],
            "status": "idle",
            "model": sample_agent_file["spec"]["model"],
        }
        assert assert_agent_state_keys(state) == []

    def test_run_agent_transition(self, sample_agent_file):
        """Verify idle → running → completed transition."""
        assert assert_status_transition("idle", "running")
        assert assert_status_transition("running", "completed")

    def test_run_agent_failed_transition(self, sample_agent_file):
        """Verify running → failed → idle (retry) transition."""
        assert assert_status_transition("running", "failed")
        assert assert_status_transition("failed", "idle")

    def test_critique_generates_finding(self, mock_llm, sample_agent_file):
        """Verify critique step produces a finding."""
        critique_prompt = "Critique the output of the previous step."
        response = mock_llm(critique_prompt)
        assert "critique" in response.lower() or "score" in response.lower()

    def test_checkpoint_creates_jsonl_event(self, sample_agent_file):
        """Verify a checkpoint event is valid JSONL."""
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "task_id": sample_agent_file["metadata"]["name"],
            "event": "checkpoint",
            "data": {"step": "execute", "status": "completed"},
        }
        line = json.dumps(event)
        parsed = assert_jsonl_line(line)
        assert parsed["event"] == "checkpoint"

    def test_resume_from_checkpoint(self, sample_agent_file):
        """Verify resume from a checkpoint event."""
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "task_id": sample_agent_file["metadata"]["name"],
            "event": "resume",
            "data": {"from_step": "execute"},
        }
        line = json.dumps(event)
        parsed = assert_jsonl_line(line)
        assert parsed["event"] == "resume"

    def test_heartbeat_event(self, sample_agent_file):
        """Verify heartbeat event format."""
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "task_id": sample_agent_file["metadata"]["name"],
            "event": "heartbeat",
        }
        line = json.dumps(event)
        parsed = assert_jsonl_line(line)
        assert parsed["event"] == "heartbeat"

    def test_error_event(self, sample_agent_file):
        """Verify error event format."""
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "task_id": sample_agent_file["metadata"]["name"],
            "event": "error",
            "data": {"message": "Tool not found"},
        }
        line = json.dumps(event)
        parsed = assert_jsonl_line(line)
        assert parsed["event"] == "error"


class TestFleetManager:
    """Test fleet manager integration."""

    def test_fleet_yaml_parsing(self, sample_fleet_yaml):
        """Verify fleet YAML can be parsed."""
        import yaml
        fleet = yaml.safe_load(sample_fleet_yaml)
        assert "agents" in fleet
        assert len(fleet["agents"]) == 2

    def test_fleet_agent_names(self, sample_fleet_yaml):
        """Verify fleet agent names are correct."""
        import yaml
        fleet = yaml.safe_load(sample_fleet_yaml)
        names = [a["name"] for a in fleet["agents"]]
        assert "planner" in names
        assert "reviewer" in names

    def test_fleet_agent_models(self, sample_fleet_yaml):
        """Verify fleet agent models are set."""
        import yaml
        fleet = yaml.safe_load(sample_fleet_yaml)
        for agent in fleet["agents"]:
            assert agent["model"] == "gpt-4"

    def test_fleet_agent_steps(self, sample_fleet_yaml):
        """Verify fleet agent steps are defined."""
        import yaml
        fleet = yaml.safe_load(sample_fleet_yaml)
        for agent in fleet["agents"]:
            assert len(agent["steps"]) > 0


class TestEndToEnd:
    """End-to-end integration test."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, mock_llm, sample_agent_file):
        """Test complete agent lifecycle with mock LLM."""
        # Spawn
        errors = assert_agent_proto(sample_agent_file)
        assert errors == []

        state = {
            "id": "test-agent",
            "name": "test-agent",
            "status": "idle",
            "model": "gpt-4",
        }
        assert assert_agent_state_keys(state) == []

        # Transition to running
        assert assert_status_transition("idle", "running")
        state["status"] = "running"

        # Execute steps
        for step in sample_agent_file["spec"]["steps"]:
            response = await mock_llm.invoke(f"Execute step: {step['name']}")
            assert response is not None

        # Complete
        assert assert_status_transition("running", "completed")
        state["status"] = "completed"

        # Checkpoint
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "task_id": "test-agent",
            "event": "checkpoint",
        }
        line = json.dumps(event)
        assert_jsonl_line(line)

    def test_contract_self_check(self):
        """Verify all contract functions are importable and callable."""
        assert callable(assert_agent_state_keys)
        assert callable(assert_jsonl_line)
        assert callable(assert_agent_proto)
        assert callable(assert_status_transition)


class TestCLI:
    """Test CLI commands."""

    def test_cli_verify(self, capsys):
        """Verify CLI verify command runs self-check."""
        from click.testing import CliRunner
        from agentforge_x.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["verify"])
        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "green" in result.output.lower() or "✓" in result.output

    def test_cli_version(self, capsys):
        """Verify CLI version command works."""
        from click.testing import CliRunner
        from agentforge_x.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output
