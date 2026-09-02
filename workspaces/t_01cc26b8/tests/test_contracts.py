"""Conformance harness tests — mock-LLM e2e + contract assertions."""
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentforge_x.contracts import (
    AGENT_STATE_REQUIRED,
    AGENT_STATE_KEYS,
    AGENT_STATUSES,
    JSONL_REQUIRED_KEYS,
    JSONL_VALID_EVENTS,
    ContractError,
    assert_agent_state_keys,
    assert_jsonl_line,
    assert_agent_proto,
    assert_status_transition,
)


class TestAssertAgentStateKeys:
    """Test AgentState key validation."""

    def test_required_keys_present(self):
        state = {"id": "1", "name": "agent", "status": "idle", "model": "gpt-4"}
        assert assert_agent_state_keys(state) == []

    def test_required_keys_missing(self):
        state = {"id": "1", "status": "idle"}
        missing = assert_agent_state_keys(state)
        assert "name" in missing
        assert "model" in missing

    def test_strict_mode_all_keys(self):
        state = {
            "id": "1", "name": "agent", "status": "idle", "model": "gpt-4",
            "instructions": "...", "tools": [], "env": {}, "steps": [],
            "current_step": None, "context": {}, "trace": [],
            "created_at": "", "updated_at": "",
        }
        assert assert_agent_state_keys(state, strict=True) == []

    def test_strict_mode_missing_keys(self):
        state = {"id": "1", "name": "agent", "status": "idle", "model": "gpt-4"}
        with pytest.raises(ContractError) as exc_info:
            assert_agent_state_keys(state, strict=True)
        assert "missing" in str(exc_info.value).lower()

    def test_status_values(self):
        assert "idle" in AGENT_STATUSES
        assert "running" in AGENT_STATUSES
        assert "completed" in AGENT_STATUSES
        assert "failed" in AGENT_STATUSES

    def test_all_statuses_valid(self):
        for status in AGENT_STATUSES:
            assert status in AGENT_STATUSES


class TestAssertJsonlLine:
    """Test JSONL event format validation."""

    def test_valid_line(self):
        line = json.dumps({
            "ts": "2026-08-30T00:00:00Z",
            "task_id": "test-123",
            "event": "heartbeat",
        })
        data = assert_jsonl_line(line)
        assert data["task_id"] == "test-123"
        assert data["event"] == "heartbeat"

    def test_empty_line(self):
        with pytest.raises(ContractError) as exc_info:
            assert_jsonl_line("")
        assert "empty" in str(exc_info.value).lower()

    def test_invalid_json(self):
        with pytest.raises(ContractError) as exc_info:
            assert_jsonl_line("{not valid json}")
        assert "json" in str(exc_info.value).lower()

    def test_missing_required_keys(self):
        line = json.dumps({"ts": "2026-08-30T00:00:00Z"})
        with pytest.raises(ContractError) as exc_info:
            assert_jsonl_line(line)
        assert "missing" in str(exc_info.value).lower()

    def test_invalid_event_type(self):
        line = json.dumps({
            "ts": "2026-08-30T00:00:00Z",
            "task_id": "test",
            "event": "invalid_event",
        })
        with pytest.raises(ContractError) as exc_info:
            assert_jsonl_line(line)
        assert "invalid" in str(exc_info.value).lower()

    def test_non_dict_json(self):
        line = json.dumps(["not", "a", "dict"])
        with pytest.raises(ContractError) as exc_info:
            assert_jsonl_line(line)
        assert "object" in str(exc_info.value).lower()

    def test_valid_event_types(self):
        """Ensure all documented event types are accepted."""
        for event in JSONL_VALID_EVENTS:
            line = json.dumps({
                "ts": "2026-08-30T00:00:00Z",
                "task_id": "test",
                "event": event,
            })
            data = assert_jsonl_line(line)
            assert data["event"] == event


class TestAssertAgentProto:
    """Test agent protocol validation."""

    def test_valid_agent(self):
        agent = {
            "apiVersion": "taskforge.dev/v1",
            "kind": "Agent",
            "metadata": {"name": "test-agent"},
            "spec": {
                "model": "gpt-4",
                "prompts": {"system": "You are an agent."},
                "steps": [{"name": "step1"}],
            },
        }
        errors = assert_agent_proto(agent)
        assert errors == []

    def test_invalid_api_version(self):
        agent = {
            "apiVersion": "v1",
            "kind": "Agent",
            "metadata": {"name": "test"},
            "spec": {"model": "gpt-4", "prompts": {}, "steps": [{"name": "s"}]},
        }
        errors = assert_agent_proto(agent)
        assert any("apiversion" in e.lower() for e in errors)

    def test_invalid_kind(self):
        agent = {
            "apiVersion": "taskforge.dev/v1",
            "kind": "Bot",
            "metadata": {"name": "test"},
            "spec": {"model": "gpt-4", "prompts": {}, "steps": [{"name": "s"}]},
        }
        errors = assert_agent_proto(agent)
        assert any("kind" in e.lower() for e in errors)

    def test_missing_metadata_name(self):
        agent = {
            "apiVersion": "taskforge.dev/v1",
            "kind": "Agent",
            "metadata": {},
            "spec": {"model": "gpt-4", "prompts": {}, "steps": [{"name": "s"}]},
        }
        errors = assert_agent_proto(agent)
        assert any("name" in e.lower() for e in errors)

    def test_missing_spec_model(self):
        agent = {
            "apiVersion": "taskforge.dev/v1",
            "kind": "Agent",
            "metadata": {"name": "test"},
            "spec": {"prompts": {}, "steps": [{"name": "s"}]},
        }
        errors = assert_agent_proto(agent)
        assert any("model" in e.lower() for e in errors)

    def test_missing_spec_prompts(self):
        agent = {
            "apiVersion": "taskforge.dev/v1",
            "kind": "Agent",
            "metadata": {"name": "test"},
            "spec": {"model": "gpt-4", "steps": [{"name": "s"}]},
        }
        errors = assert_agent_proto(agent)
        assert any("prompts" in e.lower() for e in errors)

    def test_missing_steps(self):
        agent = {
            "apiVersion": "taskforge.dev/v1",
            "kind": "Agent",
            "metadata": {"name": "test"},
            "spec": {"model": "gpt-4", "prompts": {}},
        }
        errors = assert_agent_proto(agent)
        assert any("steps" in e.lower() for e in errors)

    def test_empty_steps(self):
        agent = {
            "apiVersion": "taskforge.dev/v1",
            "kind": "Agent",
            "metadata": {"name": "test"},
            "spec": {"model": "gpt-4", "prompts": {}, "steps": []},
        }
        errors = assert_agent_proto(agent)
        assert any("empty" in e.lower() for e in errors)

    def test_step_missing_name(self):
        agent = {
            "apiVersion": "taskforge.dev/v1",
            "kind": "Agent",
            "metadata": {"name": "test"},
            "spec": {"model": "gpt-4", "prompts": {}, "steps": [{"description": "x"}]},
        }
        errors = assert_agent_proto(agent)
        assert any("step" in e.lower() and "name" in e.lower() for e in errors)


class TestStatusTransitions:
    """Test agent status transition rules."""

    def test_idle_to_running(self):
        assert assert_status_transition("idle", "running")

    def test_running_to_completed(self):
        assert assert_status_transition("running", "completed")

    def test_running_to_failed(self):
        assert assert_status_transition("running", "failed")

    def test_running_to_paused(self):
        assert assert_status_transition("running", "paused")

    def test_failed_to_idle(self):
        assert assert_status_transition("failed", "idle")

    def test_paused_to_running(self):
        assert assert_status_transition("paused", "running")

    def test_terminal_completed(self):
        assert not assert_status_transition("completed", "running")

    def test_terminal_failed_retry(self):
        assert assert_status_transition("failed", "idle")

    def test_invalid_status(self):
        assert not assert_status_transition("invalid", "running")

    def test_self_transition(self):
        """A status can transition to itself (idempotent)."""
        assert assert_status_transition("idle", "idle")
        assert assert_status_transition("running", "running")
        assert assert_status_transition("completed", "completed")
        assert assert_status_transition("failed", "failed")
        assert assert_status_transition("error", "error")
