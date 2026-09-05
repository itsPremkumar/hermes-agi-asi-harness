#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS — CONSOLIDATED AGENT FRAMEWORK
=====================================================
Merged from:
- agents/__init__.py: Role definitions, DEFAULT_ROLES, AgentRegistry
- agents/implementations.py: Agent implementations (ResearcherAgent, CoderAgent, etc.)
- core/agents.py: Legacy AgentRegistry, spawn/terminate/active helpers

All 6 agent roles with full implementations and role definitions in one place.
"""

from __future__ import annotations

import builtins
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_agents")


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES (from agents/__init__.py)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Role:
    """A specialized agent role."""
    name: str
    prompt_key: str
    toolset: str | None = None
    objective: str = ""
    system_prompt: str = ""


@dataclass
class Agent:
    """A specialized agent instance."""
    agent_id: str
    role: Role
    status: str = "active"
    spawned: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    result: str | None = None


# ═══════════════════════════════════════════════════════════════════════════
# ROLE DEFINITIONS (from agents/__init__.py)
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_ROLES: dict[str, Role] = {
    # Manager / planner
    "manager": Role("manager", "planner", None,
                    "Decompose goal, delegate to workers, supervise.",
                    "You are the Lead Systems Architect. Formulate technical architectures, state invariants, and step-by-step implementation blueprints."),

    # Research roles
    "researcher": Role("researcher", "researcher", "web",
                       "Gather real, sourced facts before acting.",
                       "You are the Lead Research Specialist. Perform rigorous analysis, extract facts, and map dependencies. Output clear, verified findings."),
    "web_searcher": Role("web_searcher", "researcher", "web",
                         "Search the web for primary sources and prior art.",
                         "You are a focused web search specialist. Find authoritative sources and primary research."),
    "data_collector": Role("data_collector", "researcher", None,
                           "Collect facts from the codebase and local data.",
                           "You are a data collector. Gather facts from the codebase, documentation, and local data sources."),

    # Coding roles
    "coder": Role("coder", "implementer", None,
                  "Propose exactly ONE falsifiable code change.",
                  "You are the Senior Implementation Engineer. Write clean, deterministic, robust Python code adhering to strict safety contracts and clean interfaces."),
    "debugger": Role("debugger", "implementer", None,
                     "Identify and fix bugs in code.",
                     "You are a debugging specialist. Identify root causes of bugs and implement fixes."),

    # Review roles
    "critic": Role("critic", "critic", None,
                   "Verify proposals against research; flag risks.",
                   "You are the Red Team Critic. Identify edge cases, race conditions, security vulnerabilities, and boundary failure modes."),
    "reviewer": Role("reviewer", "critic", None,
                     "Review code quality and architecture.",
                     "You are a code reviewer. Review code for quality, maintainability, and correctness."),
    "verifier": Role("verifier", "critic", None,
                     "Verify correctness through testing and formal methods.",
                     "You are the Verification & QA Gatekeeper. Execute test suites, verify proofs, and enforce earned-completion criteria before promotion."),

    # Analysis roles
    "analyst": Role("analyst", "annotator", None,
                    "Mine failure traces for compound patterns.",
                    "You are an analysis specialist. Find patterns in failure traces and performance data."),
    "evaluator": Role("evaluator", "annotator", None,
                      "Evaluate outcomes against acceptance criteria.",
                      "You are an evaluation specialist. Measure outcomes against defined criteria."),

    # Operations roles
    "monitor": Role("monitor", "annotator", None,
                    "Track progress and agent health.",
                    "You are a monitoring specialist. Track progress, resource usage, and agent health."),
    "planner": Role("planner", "planner", None,
                    "Create detailed execution plans.",
                    "You are a planning specialist. Create detailed, step-by-step execution plans with dependency tracking."),
}


# ═══════════════════════════════════════════════════════════════════════════
# AGENT REGISTRY (from core/agents.py - legacy module, preserved)
# ═══════════════════════════════════════════════════════════════════════════

class AgentRegistry:
    """Registry of live sub-agents."""

    def __init__(self) -> None:
        self.agents: dict[str, dict[str, object]] = {}

    def spawn(self, role: str, agent_id: str | None = None) -> str:
        aid = agent_id or ("agent_%d" % (len(self.agents) + 1))
        now = int(time.time())
        self.agents[aid] = {"role": role, "status": "active",
                            "spawned": now, "last_seen": now}
        logger.info("Agent spawned: %s (role=%s)", aid, role)
        return aid

    def terminate(self, agent_id: str) -> bool:
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "terminated"
            logger.info("Agent terminated: %s", agent_id)
            return True
        return False

    def heartbeat(self, agent_id: str) -> bool:
        if agent_id in self.agents:
            self.agents[agent_id]["last_seen"] = int(time.time())
            return True
        return False

    def active(self) -> builtins.list[str]:
        return [a for a, b in self.agents.items() if b["status"] == "active"]

    def list(self) -> dict[str, dict[str, object]]:
        return self.agents


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE HELPERS (from core/agents.py)
# ═══════════════════════════════════════════════════════════════════════════

def spawn(state: dict, role: str, agent_id: str | None = None) -> str:
    reg = state.setdefault("shared_state", {}).setdefault("_agents", AgentRegistry())
    return reg.spawn(role, agent_id)


def terminate(state: dict, agent_id: str) -> bool:
    reg = state.get("shared_state", {}).get("_agents")
    return reg.terminate(agent_id) if reg else False


def active(state: dict) -> list[str]:
    reg = state.get("shared_state", {}).get("_agents")
    return reg.active() if reg else []


# ═══════════════════════════════════════════════════════════════════════════
# ROLE CONFIG RESOLUTION (from agents/__init__.py)
# ═══════════════════════════════════════════════════════════════════════════

def get_role_config(config: dict[str, Any], name: str) -> Role:
    """Resolve a role from config overrides or defaults."""
    overrides = (config.get("roles") or {}).get(name) or {}
    base = DEFAULT_ROLES.get(name, Role(name, "implementer"))
    return Role(
        name=name,
        prompt_key=overrides.get("prompt_key", base.prompt_key),
        toolset=overrides.get("toolset", base.toolset),
        objective=overrides.get("objective", base.objective),
        system_prompt=overrides.get("system", base.system_prompt),
    )


# ═══════════════════════════════════════════════════════════════════════════
# LAZY IMPORTS — agent implementations (from implementations.py)
# ═══════════════════════════════════════════════════════════════════════════

def __getattr__(name: str) -> Any:
    """Lazy-load agent implementations to avoid circular imports."""
    _impl_map = {
        "ResearcherAgent": "implementations",
        "CoderAgent": "implementations",
        "PlannerAgent": "implementations",
        "ReviewerAgent": "implementations",
        "VerifierAgent": "implementations",
        "ExecutorAgent": "implementations",
    }
    if name in _impl_map:
        from .implementations import (  # type: ignore
            ResearcherAgent, CoderAgent, PlannerAgent, ReviewerAgent, VerifierAgent, ExecutorAgent
        )
        return locals()[name]
    raise AttributeError(f"module 'core.agents' has no attribute {name!r}")