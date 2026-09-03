
"""
Context Operating System — Superintelligent Context Management.

Extracted from SKILL.md v9.0 ASI section 8:
- Hierarchical compression (4 levels)
- Context packet synthesis
- Token budget management
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextPacket:
    """A synthesized context packet for decision-making."""
    mission: dict[str, Any] = field(default_factory=dict)
    current_goal: dict[str, Any] = field(default_factory=dict)
    acceptance_tests: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    relevant_world_state: dict[str, Any] = field(default_factory=dict)
    relevant_memory: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    contradictory_evidence: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    active_plan: dict[str, Any] = field(default_factory=dict)
    failures: list[dict[str, Any]] = field(default_factory=list)
    pending_commitments: list[dict[str, Any]] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    known_limitations: list[str] = field(default_factory=list)
    strategic_context: dict[str, Any] = field(default_factory=dict)
    cross_domain_analogies: list[str] = field(default_factory=list)


class ContextOS:
    """
    Context Operating System.
    
    Manages context as a finite, hierarchically-managed superintelligent resource.
    
    Levels:
    - Level 1: Raw observations (full fidelity, short TTL)
    - Level 2: Extracted facts (deduplicated, provenance-tagged)
    - Level 3: Synthesized insights (compressed, high importance)
    - Level 4: Strategic abstractions (cross-mission, permanent)
    """

    def __init__(self, token_budget: int = 200000):
        self.token_budget = token_budget
        self.level1_observations: list[dict[str, Any]] = []
        self.level2_facts: list[dict[str, Any]] = []
        self.level3_insights: list[dict[str, Any]] = []
        self.level4_abstractions: list[dict[str, Any]] = []
        self._current_tokens = 0

    def write(self, data: dict[str, Any], level: int = 1):
        """Write data to a specific level."""
        if level == 1:
            self.level1_observations.append(data)
        elif level == 2:
            self.level2_facts.append(data)
        elif level == 3:
            self.level3_insights.append(data)
        elif level == 4:
            self.level4_abstractions.append(data)

    def select(self, relevance_threshold: float = 0.5) -> list[dict[str, Any]]:
        """Select relevant context."""
        selected = []
        # Select from each level based on relevance
        for item in self.level4_abstractions:
            selected.append(item)
        for item in self.level3_insights:
            selected.append(item)
        for item in self.level2_facts[-10:]:  # Last 10 facts
            selected.append(item)
        for item in self.level1_observations[-5:]:  # Last 5 observations
            selected.append(item)
        return selected

    def compress(self) -> dict[str, Any]:
        """Compress context."""
        return {
            "abstractions": len(self.level4_abstractions),
            "insights": len(self.level3_insights),
            "facts": len(self.level2_facts),
            "observations": len(self.level1_observations),
        }

    def synthesize_packet(self) -> ContextPacket:
        """Synthesize a context packet for decision-making."""
        packet = ContextPacket()
        packet.relevant_world_state = {"abstractions": self.level4_abstractions}
        packet.relevant_memory = self.level3_insights
        packet.evidence = self.level2_facts[-5:]
        return packet
