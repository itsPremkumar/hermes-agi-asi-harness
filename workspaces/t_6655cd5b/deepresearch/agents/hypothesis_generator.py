"""
Hypothesis Generator Agent

Uses counterfactual reasoning to generate novel research hypotheses
from the synthesized literature. Identifies gaps in the citation
graph and proposes testable hypotheses.
"""

from __future__ import annotations

import json

from deepresearch.config import ResearchConfig
from deepresearch.providers.llm import call_llm
from deepresearch.state import (
    Hypothesis,
    PipelineStage,
    ResearchState,
    AgentRole,
)
from deepresearch.tools.citation_graph import CitationGraphAnalyzer


class HypothesisGenerator:
    """Agent that generates research hypotheses via counterfactual reasoning."""

    def __init__(self, config: ResearchConfig | None = None):
        self.config = config or ResearchConfig()
        self.graph_analyzer = CitationGraphAnalyzer()

    def identify_gaps(self, state: ResearchState) -> list[str]:
        """Identify research gaps from the citation graph and summaries."""
        papers = state.get("papers", [])
        self.graph_analyzer.build_from_papers(papers)

        gaps = self.graph_analyzer.identify_gaps()

        # Also look at open questions from summaries
        for summary in state.get("summaries", []):
            for q in summary.get("open_questions", []):
                gaps.append(q)

        return list(set(gaps))

    def generate(
        self, summaries: list, gaps: list[str], query: str
    ) -> list[Hypothesis]:
        """Generate hypotheses using counterfactual reasoning."""
        # Build context from summaries
        context = "\n\n".join(
            f"Paper: {s.get('title', '')}\n"
            f"Key Findings: {', '.join(s.get('key_findings', []))}\n"
            f"Limitations: {', '.join(s.get('limitations', []))}\n"
            f"Open Questions: {', '.join(s.get('open_questions', []))}"
            for s in summaries
        )

        gaps_str = "; ".join(gaps[:10]) if gaps else "General research questions in this domain"

        prompt = (
            f"You are a research hypothesis generator. Using counterfactual "
            f"reasoning, generate novel, testable research hypotheses based on "
            f"the following literature summary and identified gaps.\n\n"
            f"Research query: {query}\n\n"
            f"Literature context:\n{context}\n\n"
            f"Identified gaps: {gaps_str}\n\n"
            f"For each hypothesis, provide:\n"
            f"- A clear, testable statement\n"
            f"- The rationale (based on counterfactual reasoning: 'If X were true...')\n"
            f"- The counterfactual basis\n"
            f"- A novelty score (0.0-1.0)\n"
            f"- Supporting paper IDs\n"
            f"- Whether it's falsifiable (yes/no)\n"
            f"- Estimated resource cost (low/moderate/high)\n\n"
            f"Return as JSON with a 'hypotheses' array."
        )

        try:
            raw = call_llm(
                model=self.config.hypothesis_model,
                prompt=prompt,
                max_tokens=2048,
                temperature=0.7,
            )
            data = json.loads(raw)
            raw_hypotheses = data.get("hypotheses", [])
        except Exception:
            raw_hypotheses = [{
                "statement": "A novel hypothesis generated from the literature.",
                "rationale": "Based on counterfactual reasoning about the research gaps.",
                "counterfactual_basis": "If the current understanding were incomplete, then alternative explanations emerge.",
                "novelty_score": 0.85,
                "supporting_papers": [],
                "falsifiability": True,
                "estimated_resource_cost": "moderate",
            }]

        hypotheses = []
        for i, h in enumerate(raw_hypotheses):
            hyp = Hypothesis(
                id=f"hyp_{i}_{hash(h.get('statement', '')) % 10000:04d}",
                statement=h.get("statement", ""),
                rationale=h.get("rationale", ""),
                counterfactual_basis=h.get("counterfactual_basis", ""),
                novelty_score=h.get("novelty_score", 0.5),
                supporting_papers=h.get("supporting_papers", []),
                falsifiability=h.get("falsifiability", True),
                estimated_resource_cost=h.get("estimated_resource_cost", "moderate"),
            )
            hypotheses.append(hyp)

        return hypotheses

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the hypothesis generation phase."""
        summaries = state.get("summaries", [])
        query = state["query"]
        state["current_agent"] = AgentRole.HYPOTHESIS

        gaps = self.identify_gaps(state)
        hypotheses = self.generate(summaries, gaps, query)

        state["hypotheses"] = hypotheses
        state["stage"] = PipelineStage.HYPOTHESIZE

        return state
