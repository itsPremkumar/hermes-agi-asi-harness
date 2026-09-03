"""
Evolution Candidate Generator + Population Archive — Sections 65-67 of v7 spec

Candidate records with parent tracking, change classification, expected gain.
Population diversity, Pareto fitness vectors.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvolutionCandidate:
    """An evolution candidate."""
    id: str
    parent: str
    change_type: str  # planner, memory, tool, agent, workflow, etc.
    hypothesis_id: str
    changed_components: list[str]
    expected_gain: float = 0.0
    dev_score: float = 0.0
    holdout_score: float = 0.0
    novel_score: float = 0.0
    regression: bool = False
    safety_pass: bool = False
    decision: str = "pending"  # pending, promote, reject
    created_at: float = field(default_factory=time.time)


class PopulationArchive:
    """Archive of evolution candidates with diversity tracking."""

    def __init__(self):
        self._candidates: dict[str, EvolutionCandidate] = {}
        self._lineages: dict[str, list[str]] = {}  # parent → [child_ids]
        self._promoted: list[str] = []
        self._rejected: list[str] = []

    def create_candidate(
        self,
        parent: str,
        change_type: str,
        hypothesis_id: str,
        changed_components: list[str],
        expected_gain: float = 0.0,
    ) -> EvolutionCandidate:
        """Create a new evolution candidate."""
        candidate = EvolutionCandidate(
            id=f"EVO-{uuid.uuid4().hex[:8]}",
            parent=parent,
            change_type=change_type,
            hypothesis_id=hypothesis_id,
            changed_components=changed_components,
            expected_gain=expected_gain,
        )
        self._candidates[candidate.id] = candidate
        
        # Track lineage
        if parent not in self._lineages:
            self._lineages[parent] = []
        self._lineages[parent].append(candidate.id)
        
        return candidate

    def evaluate_candidate(self, candidate_id: str, dev_score: float, holdout_score: float, novel_score: float, regression: bool, safety_pass: bool):
        """Record evaluation results."""
        c = self._candidates.get(candidate_id)
        if not c:
            return
        
        c.dev_score = dev_score
        c.holdout_score = holdout_score
        c.novel_score = novel_score
        c.regression = regression
        c.safety_pass = safety_pass
        
        # Auto-decide
        if safety_pass and not regression and holdout_score > 0.5:
            c.decision = "promote"
            self._promoted.append(candidate_id)
        else:
            c.decision = "reject"
            self._rejected.append(candidate_id)

    def get_pareto_frontier(self) -> list[EvolutionCandidate]:
        """Get candidates on the Pareto frontier."""
        candidates = [c for c in self._candidates.values() if c.decision == "pending"]
        if not candidates:
            return []
        
        # Simple Pareto: not dominated on all objectives
        pareto = []
        for c in candidates:
            dominated = False
            for other in candidates:
                if other.id == c.id:
                    continue
                if (other.dev_score >= c.dev_score 
                    and other.holdout_score >= c.holdout_score
                    and other.novel_score >= c.novel_score):
                    dominated = True
                    break
            if not dominated:
                pareto.append(c)
        
        return pareto

    def get_diversity(self) -> dict[str, int]:
        """Measure population diversity by change type."""
        diversity = {}
        for c in self._candidates.values():
            diversity[c.change_type] = diversity.get(c.change_type, 0) + 1
        return diversity

    def get_candidate(self, candidate_id: str) -> EvolutionCandidate | None:
        return self._candidates.get(candidate_id)

    def get_lineage(self, candidate_id: str) -> list[str]:
        """Get full lineage of a candidate."""
        lineage = []
        c = self._candidates.get(candidate_id)
        while c:
            lineage.append(c.id)
            c = self._candidates.get(c.parent)
        return list(reversed(lineage))

    def get_stats(self) -> dict[str, Any]:
        return {
            "total": len(self._candidates),
            "promoted": len(self._promoted),
            "rejected": len(self._rejected),
            "pending": sum(1 for c in self._candidates.values() if c.decision == "pending"),
            "lineages": len(self._lineages),
            "diversity": self.get_diversity(),
        }


class EvolutionArchivePlugin:
    def __init__(self):
        self.archive = PopulationArchive()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.archive.get_stats()}

    async def create_candidate(self, **kwargs):
        return self.archive.create_candidate(**kwargs)

    async def evaluate(self, **kwargs):
        self.archive.evaluate_candidate(**kwargs)

    async def get_pareto(self):
        return self.archive.get_pareto_frontier()


async def create(kernel=None):
    plugin = EvolutionArchivePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
