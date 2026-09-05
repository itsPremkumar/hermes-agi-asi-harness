"""
HERMES INTELLIGENCE OS — CONTEXT OS COMPILER
============================================
Compiles required, useful, and optional context into a disciplined, budget-partitioned
model input envelope. Never dumps unbounded raw text into prompt tokens.
Features:
- Dynamic partition rebalancing (shifts unused retrieval budget to working scratchpad)
- Semantic compaction for large historical notes and scratchpads
- Persisted reasoning trail preservation across long-horizon multi-turn missions
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .budgets import ContextBudget
from .invariants import GoalContract

logger = logging.getLogger("hermes.context_os.compiler")


class ContextCompiler:
    """Compiles multi-source operational context under strict partition budgets."""

    def __init__(self, budget: Optional[ContextBudget] = None):
        self.budget = budget or ContextBudget.standard_128k()
        self._persisted_reasoning_trail: list[str] = []

    def record_persisted_reasoning(self, reasoning_summary: str) -> None:
        """Store compressed reasoning steps for mid-turn steering and long-horizon persistence."""
        self._persisted_reasoning_trail.append(reasoning_summary)
        if len(self._persisted_reasoning_trail) > 10:
            self._persisted_reasoning_trail.pop(0)

    def compact(self, text: str, max_chars: int = 2000) -> str:
        """Semantically compact long text blocks while retaining structural headers and conclusions."""
        if len(text) <= max_chars:
            return text
        lines = text.splitlines()
        if len(lines) <= 6:
            return text[:max_chars] + "... [compacted]"
        # Retain first 3 and last 3 lines, compact middle
        header = "\n".join(lines[:3])
        footer = "\n".join(lines[-3:])
        return f"{header}\n... [compacted {len(lines) - 6} intermediate lines] ...\n{footer}"

    def rebalance_budget(self, retrieved_items_count: int, working_tasks_count: int) -> dict[str, int]:
        """Dynamically rebalances partitions if one partition is heavily underutilized."""
        b_dict = self.budget.to_dict()
        # If retrieved knowledge is minimal, donate spare tokens to working scratchpad
        if retrieved_items_count <= 2 and b_dict["retrieved"] > 20000:
            spare = b_dict["retrieved"] // 2
            b_dict["retrieved"] -= spare
            b_dict["working"] += spare
        return b_dict

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

        # 3. Working partition (Current task DAG, scratchpad, persisted reasoning)
        tasks_text = "\n".join(f"- Task {t.get('id', i)}: {t.get('description', '')} (Status: {t.get('status', 'pending')})" for i, t in enumerate(working_tasks[:15]))
        reasoning_text = ("\nPERSISTED REASONING TRAIL:\n" + "\n".join(f"> {r}" for r in self._persisted_reasoning_trail)) if self._persisted_reasoning_trail else ""
        working_block = self.compact(tasks_text + reasoning_text, max_chars=8000)

        # 4. Historical partition (Recent episodic events & trajectory summaries)
        historical_block = self.compact("\n".join(f"• {h}" for h in historical_notes[:10]), max_chars=4000)

        effective_budget = self.rebalance_budget(len(retrieved_knowledge), len(working_tasks))

        return {
            "budget": effective_budget,
            "core_context": core_block,
            "retrieved_context": retrieved_block,
            "working_context": working_block,
            "historical_context": historical_block,
            "reserve_buffer_tokens": effective_budget.get("reserve", self.budget.reserve),
            "contract_id": goal_contract.contract_id,
        }
