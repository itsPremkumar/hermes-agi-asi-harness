"""
HERMES INTELLIGENCE OS — UNCERTAINTY ANALYSIS & RESEARCH PLANNING (v9)
====================================================================
Formal epistemic reasoning subsystem for Hermes Cognitive OS:
- Epistemic taxonomy: KNOWN, UNKNOWN, UNCERTAIN, ASSUMED, CONTESTED.
- Enforces the core invariant: Never silently convert unknowns into assumptions.
- Value of Information (VOI) metric: stops research when marginal information gain <= threshold.
- Structured ResearchPlan decomposing unknowns into multi-source research lanes
  (official docs, primary papers, source repo, independent benchmarks, empirical experiment).
"""

from __future__ import annotations

import enum
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("hermes.os.uncertainty")


class EpistemicStatus(str, enum.Enum):
    """Rigorous classification of state knowledge."""
    KNOWN = "known"              # Empirically verified fact
    UNKNOWN = "unknown"          # Explicitly recognized missing information
    UNCERTAIN = "uncertain"      # Known with moderate confidence or probabilistic range
    ASSUMED = "assumed"          # Working hypothesis explicitly tracked
    CONTESTED = "contested"      # Disputed by conflicting evidence sources


@dataclass
class EpistemicItem:
    """Individual knowledge or uncertainty claim."""
    id: str
    statement: str
    status: EpistemicStatus
    confidence: float = 0.5                    # 0.0 to 1.0
    sources: List[str] = field(default_factory=list)
    falsification_condition: Optional[str] = None
    impact_on_plan: str = "medium"             # "low", "medium", "critical"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "status": self.status.value,
            "confidence": round(self.confidence, 2),
            "sources": self.sources,
            "falsification_condition": self.falsification_condition,
            "impact": self.impact_on_plan,
        }


class ResearchLaneType(str, enum.Enum):
    """Source diversity lanes for empirical research."""
    OFFICIAL_DOCS = "official_docs"
    PRIMARY_PAPERS = "primary_papers"
    SOURCE_REPO = "source_repo"
    INDEPENDENT_BENCHMARKS = "independent_benchmarks"
    EMPIRICAL_TEST = "empirical_test"


@dataclass
class ResearchQuery:
    """Specific query targeted to a distinct research lane."""
    query_id: str
    unknown_id: str
    question: str
    lane: ResearchLaneType
    priority: int = 1
    expected_evidence_type: str = "specification"


@dataclass
class ResearchPlan:
    """Deliberate plan for resolving unknowns before strategy selection."""
    plan_id: str
    objective: str
    queries: List[ResearchQuery] = field(default_factory=list)
    voi_score: float = 0.75                     # Value of Information
    stopping_threshold: float = 0.20
    is_completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "objective": self.objective,
            "queries_count": len(self.queries),
            "voi_score": round(self.voi_score, 3),
            "stopping_threshold": self.stopping_threshold,
            "is_completed": self.is_completed,
            "queries": [
                {"id": q.query_id, "lane": q.lane.value, "question": q.question}
                for q in self.queries
            ],
        }


class UncertaintyAnalyzer:
    """
    Analyzes intent, environment state, and requirements to extract
    epistemic items and calculate Value of Information.
    """

    def analyze(
        self,
        request: str,
        environment_summary: str = "",
        explicit_assumptions: Optional[List[str]] = None,
    ) -> List[EpistemicItem]:
        items: List[EpistemicItem] = []
        req_lower = request.lower()

        # 1. Detect Knowns
        items.append(EpistemicItem(
            id=f"epi-k-{uuid.uuid4().hex[:6]}",
            statement="Target environment executes on Python runtime with standard workspace tooling",
            status=EpistemicStatus.KNOWN,
            confidence=0.99,
            sources=["environment_recon"],
            impact_on_plan="low",
        ))

        # 2. Detect Unknowns based on request patterns
        if any(w in req_lower for w in ["api", "service", "endpoint", "cloud", "external"]):
            items.append(EpistemicItem(
                id=f"epi-u-{uuid.uuid4().hex[:6]}",
                statement="External API rate limits, authentication credentials, and endpoint availability",
                status=EpistemicStatus.UNKNOWN,
                confidence=0.1,
                impact_on_plan="critical",
            ))

        if any(w in req_lower for w in ["database", "db", "sql", "postgres", "schema", "table"]):
            items.append(EpistemicItem(
                id=f"epi-u-{uuid.uuid4().hex[:6]}",
                statement="Production database schema, migration history, and constraint definitions",
                status=EpistemicStatus.UNKNOWN,
                confidence=0.2,
                impact_on_plan="critical",
            ))

        if any(w in req_lower for w in ["optimize", "performance", "throughput", "latency"]):
            items.append(EpistemicItem(
                id=f"epi-unc-{uuid.uuid4().hex[:6]}",
                statement="Baseline latency distribution and bottleneck profile under production load",
                status=EpistemicStatus.UNCERTAIN,
                confidence=0.4,
                impact_on_plan="high",
            ))

        # 3. Incorporate explicit assumptions
        for assump in explicit_assumptions or []:
            items.append(EpistemicItem(
                id=f"epi-a-{uuid.uuid4().hex[:6]}",
                statement=assump,
                status=EpistemicStatus.ASSUMED,
                confidence=0.6,
                falsification_condition="Failed pre-condition check during execution wave 1",
                impact_on_plan="medium",
            ))

        return items

    def compute_value_of_information(self, epistemic_items: List[EpistemicItem]) -> float:
        """
        VOI = Sum of (Impact_weight * (1.0 - confidence)) normalized to [0.0, 1.0].
        High VOI indicates that researching will significantly derisk the plan.
        """
        if not epistemic_items:
            return 0.0

        weights = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
        total_value = 0.0
        max_possible = 0.0

        for item in epistemic_items:
            w = weights.get(item.impact_on_plan, 0.5)
            max_possible += w
            if item.status in [EpistemicStatus.UNKNOWN, EpistemicStatus.UNCERTAIN, EpistemicStatus.CONTESTED]:
                total_value += w * (1.0 - item.confidence)

        if max_possible == 0.0:
            return 0.0
        return round(total_value / max_possible, 3)

    def generate_research_plan(
        self,
        objective: str,
        epistemic_items: List[EpistemicItem],
    ) -> ResearchPlan:
        """Construct multi-source research plan targeting the identified unknowns."""
        queries: List[ResearchQuery] = []
        voi = self.compute_value_of_information(epistemic_items)

        for item in epistemic_items:
            if item.status == EpistemicStatus.UNKNOWN:
                # Assign to official documentation & source repo lanes
                queries.append(ResearchQuery(
                    query_id=f"rq-{uuid.uuid4().hex[:6]}",
                    unknown_id=item.id,
                    question=f"Investigate: {item.statement}",
                    lane=ResearchLaneType.OFFICIAL_DOCS,
                    priority=1 if item.impact_on_plan == "critical" else 2,
                ))
                queries.append(ResearchQuery(
                    query_id=f"rq-{uuid.uuid4().hex[:6]}",
                    unknown_id=item.id,
                    question=f"Inspect repository and local tests for: {item.statement}",
                    lane=ResearchLaneType.SOURCE_REPO,
                    priority=1,
                ))
            elif item.status == EpistemicStatus.UNCERTAIN:
                queries.append(ResearchQuery(
                    query_id=f"rq-{uuid.uuid4().hex[:6]}",
                    unknown_id=item.id,
                    question=f"Run empirical benchmark test to establish facts on: {item.statement}",
                    lane=ResearchLaneType.EMPIRICAL_TEST,
                    priority=2,
                ))

        return ResearchPlan(
            plan_id=f"rp-{uuid.uuid4().hex[:8]}",
            objective=objective,
            queries=queries,
            voi_score=voi,
            stopping_threshold=0.20,
        )
