"""AgentForge-X Conformance Harness — executable contract assertions.

This module provides runtime contract checks for the AgentForge-X platform:
- AgentState key validation
- JSONL event format assertions
- Agent protocol conformance
"""
from __future__ import annotations

import json
from typing import Any

# Canonical AgentState keys (from SDK contract at 3cf99c7)
AGENT_STATE_KEYS = {
    "id",
    "name",
    "status",
    "model",
    "instructions",
    "tools",
    "env",
    "steps",
    "current_step",
    "context",
    "trace",
    "created_at",
    "updated_at",
}

# Required keys (minimal valid state)
AGENT_STATE_REQUIRED = {"id", "name", "status", "model"}

# Valid status values
AGENT_STATUSES = {"idle", "running", "paused", "completed", "failed", "error"}

# JSONL event format (from scan-contract.md)
JSONL_REQUIRED_KEYS = {"ts", "task_id", "event"}
JSONL_VALID_EVENTS = {
    "task_created",
    "task_started",
    "task_completed",
    "task_failed",
    "task_blocked",
    "heartbeat",
    "step_started",
    "step_completed",
    "step_failed",
    "tool_called",
    "tool_result",
    "checkpoint",
    "resume",
    "error",
}


class ContractError(Exception):
    """Raised when a contract assertion fails."""
    pass


def assert_agent_state_keys(state: dict[str, Any], strict: bool = False) -> list[str]:
    """Validate that an AgentState dict has the required keys.
    
    Args:
        state: The agent state dictionary to validate
        strict: If True, require all canonical keys; if False, only required keys
        
    Returns:
        List of missing keys (empty if valid)
        
    Raises:
        ContractError: If validation fails and strict=True
    """
    required = AGENT_STATE_KEYS if strict else AGENT_STATE_REQUIRED
    missing = [k for k in required if k not in state]
    
    if missing:
        msg = f"AgentState missing required keys: {missing}"
        if strict:
            raise ContractError(msg)
        return missing
    return []


def assert_jsonl_line(line: str) -> dict[str, Any]:
    """Parse and validate a JSONL event line.
    
    Args:
        line: A single JSONL line string
        
    Returns:
        The parsed JSON dict
        
    Raises:
        ContractError: If the line is not valid JSONL or missing required fields
    """
    if not line or not line.strip():
        raise ContractError("Empty JSONL line")
    
    try:
        data = json.loads(line.strip())
    except json.JSONDecodeError as e:
        raise ContractError(f"Invalid JSON in JSONL line: {e}")
    
    if not isinstance(data, dict):
        raise ContractError(f"JSONL line must be a JSON object, got {type(data).__name__}")
    
    missing = [k for k in JSONL_REQUIRED_KEYS if k not in data]
    if missing:
        raise ContractError(f"JSONL event missing required keys: {missing}")
    
    if data["event"] not in JSONL_VALID_EVENTS:
        raise ContractError(
            f"Invalid JSONL event type: {data['event']}. "
            f"Valid types: {JSONL_VALID_EVENTS}"
        )
    
    return data


def assert_agent_proto(agent: dict[str, Any]) -> list[str]:
    """Validate an agent definition against the .agent file schema.
    
    Args:
        agent: The agent definition dict (parsed from .agent.yml)
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check apiVersion
    if agent.get("apiVersion") != "taskforge.dev/v1":
        errors.append(f"Invalid apiVersion: expected 'taskforge.dev/v1', got '{agent.get('apiVersion')}'")
    
    # Check kind
    if agent.get("kind") != "Agent":
        errors.append(f"Invalid kind: expected 'Agent', got '{agent.get('kind')}'")
    
    # Check metadata
    metadata = agent.get("metadata", {})
    if not metadata.get("name"):
        errors.append("metadata.name is required")
    
    # Check spec
    spec = agent.get("spec", {})
    if not spec.get("model"):
        errors.append("spec.model is required")
    if not spec.get("prompts"):
        errors.append("spec.prompts is required")
    
    # Check steps
    steps = spec.get("steps", [])
    if not steps:
        errors.append("spec.steps must not be empty")
    
    for i, step in enumerate(steps):
        if not step.get("name"):
            errors.append(f"steps[{i}].name is required")
    
    return errors


def assert_status_transition(from_status: str, to_status: str) -> bool:
    """Check if a status transition is valid.
    
    Args:
        from_status: Current status
        to_status: Target status
        
    Returns:
        True if the transition is valid
    """
    valid_transitions = {
        "idle": {"idle", "running", "error"},
        "running": {"running", "paused", "completed", "failed", "error"},
        "paused": {"paused", "running", "failed", "error"},
        "completed": {"completed"},  # terminal
        "failed": {"failed", "idle"},  # can retry
        "error": {"error", "idle"},   # can retry
    }
    
    if from_status not in AGENT_STATUSES:
        return False
    if to_status not in AGENT_STATUSES:
        return False
    
    return to_status in valid_transitions.get(from_status, set())
