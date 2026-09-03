#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS — AGENT FACTORY
========================================
Creates and manages specialized agent roles.

Extracted from:
- agx-harness-main: Role registry, DEFAULT_ROLES
- hermes-super-harness: DeerFlow agents (planner, researcher, coder, reviewer, verifier)
- hermes-asi-master: SpecialistRole (researcher, planner, coder, critic, evaluator)
"""

from __future__ import annotations

import builtins
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_agents")


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


# ═══════════════════════════════════════════════════════════════════════════════════
# ROLE DEFINITIONS (from agx-harness-main + hermes-asi-master)
# ═══════════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════════

class AgentRegistry:
    """Registry of live agents."""
    
    def __init__(self):
        self.agents: dict[str, Agent] = {}
    
    def spawn(self, role_name: str, agent_id: str | None = None) -> str:
        """Spawn a new agent with the given role."""
        role = DEFAULT_ROLES.get(role_name)
        if not role:
            logger.warning("Unknown role: %s, defaulting to manager", role_name)
            role = DEFAULT_ROLES["manager"]
        
        aid = agent_id or f"agent_{role_name}_{int(time.time())}"
        agent = Agent(agent_id=aid, role=role)
        self.agents[aid] = agent
        
        logger.info("Agent spawned: %s (role=%s)", aid, role_name)
        return aid
    
    def terminate(self, agent_id: str) -> bool:
        """Terminate an agent."""
        if agent_id in self.agents:
            self.agents[agent_id].status = "terminated"
            logger.info("Agent terminated: %s", agent_id)
            return True
        return False
    
    def heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat."""
        if agent_id in self.agents:
            self.agents[agent_id].last_seen = time.time()
            return True
        return False
    
    def active(self) -> builtins.list[str]:
        """Get list of active agent IDs."""
        return [a for a, b in self.agents.items() if b.status == "active"]
    
    def list(self) -> dict[str, Agent]:
        """List all agents."""
        return self.agents
    
    def get_by_role(self, role_name: str) -> builtins.list[Agent]:
        """Get all agents with a specific role."""
        return [a for a in self.agents.values() if a.role.name == role_name]
    
    def get_role_config(self, config: dict[str, Any], name: str) -> Role:
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
