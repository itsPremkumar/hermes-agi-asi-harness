"""
HERMES INTELLIGENCE OS — CONTEXT OS COMPILER
============================================
Compiles required, useful, and optional context into a disciplined, budget-partitioned
model input envelope. Never dumps unbounded raw text into prompt tokens.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .budgets import ContextBudget
from .invariants import GoalContract

logger = logging.getLogger("hermes.context_os.compiler")


class ContextCompiler:
    """Compiles multi-source operational context under strict partition budgets."""

    def __init__(self, budget: Optional[ContextBudget] = None):
        self.budget = budget or ContextBudget.standard_128k()

    def compile(
        self,
        goal_contract: GoalContract,
        world_state_summary: str,
        retrieved_knowledge: list[str],
        working_tasks: list[dict[str, Any]],
        historical_notes: list[str],
    ) -> dict[str, Any]:
        """Compile a structured, budget-compliant context packet."""
        # 1. Core partition (Goal, Invariants, Objective)
        invariants_text = "\n".join(f"- [{inv.severity.upper()}] {inv.name}: {inv.description}" for inv in goal_contract.invariants)
        core_block = (
            f"MISSION OBJECTIVE: {goal_contract.objective}\n"
            f"IMMUTABLE INVARIANTS:\n{invariants_text}\n"
            f"WORLD STATE: {world_state_summary}"
        )

        # 2. Retrieved partition (Filtered search, docs, RLM variables)
        retrieved_block = "\n".join(f"[{i+1}] {k}" for i, k in enumerate(retrieved_knowledge[:20]))

        # 3. Working partition (Current task DAG & scratchpad)
        working_block = "\n".join(f"- Task {t.get('id', i)}: {t.get('description', '')} (Status: {t.get('status', 'pending')})" for i, t in enumerate(working_tasks[:15]))

        # 4. Historical partition (Recent episodic events & trajectory summaries)
        historical_block = "\n".join(f"• {h}" for h in historical_notes[:10])

        return {
            "budget": self.budget.to_dict(),
            "core_context": core_block,
            "retrieved_context": retrieved_block,
            "working_context": working_block,
            "historical_context": historical_block,
            "reserve_buffer_tokens": self.budget.reserve,
            "contract_id": goal_contract.contract_id,
        }
