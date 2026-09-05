"""
HERMES INTELLIGENCE OS — DYNAMIC CONTEXT BUDGETS
================================================
Inspired by the GPT-6 Astra 1.05M-token context handling principles:
Partitions finite context space dynamically so that retrieval, working scratchpad,
historical trajectory, and safety reserve never starve core system instructions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("hermes.context_os.budgets")


@dataclass
class ContextBudget:
    """Dynamic token partitions for superintelligent context compilation."""
    total_tokens: int = 128000
    core: int = 20000       # System policy, role prompts, invariants
    retrieved: int = 50000  # Documentation, search findings, RLM outputs
    working: int = 35000    # Active task DAG, current observations, scratchpad
    historical: int = 15000 # Past episodic events and previous trajectories
    reserve: int = 8000     # Buffer for recovery, error diagnostics, safety

    def validate(self) -> bool:
        allocated = self.core + self.retrieved + self.working + self.historical + self.reserve
        return allocated <= self.total_tokens

    @classmethod
    def standard_128k(cls) -> "ContextBudget":
        return cls(total_tokens=128000, core=20000, retrieved=50000, working=35000, historical=15000, reserve=8000)

    @classmethod
    def deep_reason_200k(cls) -> "ContextBudget":
        return cls(total_tokens=200000, core=25000, retrieved=85000, working=55000, historical=25000, reserve=10000)

    @classmethod
    def astra_frontier_1m(cls) -> "ContextBudget":
        return cls(total_tokens=1050000, core=100000, retrieved=450000, working=350000, historical=100000, reserve=50000)

    def to_dict(self) -> dict[str, int]:
        return {
            "total_tokens": self.total_tokens,
            "core": self.core,
            "retrieved": self.retrieved,
            "working": self.working,
            "historical": self.historical,
            "reserve": self.reserve,
        }
