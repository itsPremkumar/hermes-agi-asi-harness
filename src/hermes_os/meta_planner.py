"""
HERMES INTELLIGENCE OS — META-PLANNER (ARCHITECTURE SELECTION)
==============================================================
Before solving a task, Hermes selects:
MODEL + AGENT TOPOLOGY + TOOLS + PLANNING MODE + REASONING MODE + VERIFICATION LEVEL + COMPUTE BUDGET.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from context_os.budgets import ContextBudget
from verification.vnext import VerificationTier

logger = logging.getLogger("hermes.os.meta_planner")


@dataclass
class ExecutionArchitecture:
    """The synthesized execution envelope for a mission."""
    model_tier: str            # reactive, deep_reason, frontier_astra
    agent_topology: str        # solo_specialist, hierarchical_swarm, dialectical_debate
    tools: list[str]
    planning_mode: str         # linear, mcts_graph_of_thought, reactive
    reasoning_mode: str        # deductive, causal, counterfactual, programmatic
    verification_tier: VerificationTier
    context_budget: ContextBudget
    max_agent_slots: int = 4
    timeout_seconds: int = 120

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_tier": self.model_tier,
            "agent_topology": self.agent_topology,
            "tools": self.tools,
            "planning_mode": self.planning_mode,
            "reasoning_mode": self.reasoning_mode,
            "verification_tier": self.verification_tier.value,
            "context_budget": self.context_budget.to_dict(),
            "max_agent_slots": self.max_agent_slots,
            "timeout_seconds": self.timeout_seconds,
        }


class MetaPlanner:
    """Selects the optimal cognitive and computational topology for any given mission."""

    def __init__(self):
        pass

    def select_architecture(self, task_description: str, risk_level: str = "medium") -> ExecutionArchitecture:
        desc_lower = task_description.lower()

        # 1. Complexity & Domain classification
        is_deep = any(k in desc_lower for k in ("prove", "theorem", "refactor", "optimize", "architecture", "distributed", "consensus"))
        is_code = any(k in desc_lower for k in ("code", "implement", "build", "kernel", "fix", "debug", "test"))
        is_security = any(k in desc_lower for k in ("auth", "security", "permission", "crypto", "sandbox"))

        # 2. Model & Compute
        if is_security or risk_level == "critical":
            model_tier = "frontier_astra"
            topology = "dialectical_debate"
            planning = "mcts_graph_of_thought"
            reasoning = "counterfactual"
            v_tier = VerificationTier.L5_DETERMINISTIC_ORACLE
            budget = ContextBudget.deep_reason_200k()
            tools = ["permission_sandbox", "anti_goodhart", "python_tool", "rlm_repl", "audit_logger"]
        elif is_deep:
            model_tier = "deep_reason"
            topology = "hierarchical_swarm"
            planning = "mcts_graph_of_thought"
            reasoning = "causal"
            v_tier = VerificationTier.L5_DETERMINISTIC_ORACLE
            budget = ContextBudget.deep_reason_200k()
            tools = ["python_tool", "rlm_repl", "filesystem_tool", "benchmarks"]
        else:
            model_tier = "reactive"
            topology = "solo_specialist"
            planning = "linear"
            reasoning = "programmatic"
            v_tier = VerificationTier.L1_SELF_CHECK
            budget = ContextBudget.standard_128k()
            tools = ["python_tool", "filesystem_tool", "shell_tool"]

        return ExecutionArchitecture(
            model_tier=model_tier,
            agent_topology=topology,
            tools=tools,
            planning_mode=planning,
            reasoning_mode=reasoning,
            verification_tier=v_tier,
            context_budget=budget,
        )
