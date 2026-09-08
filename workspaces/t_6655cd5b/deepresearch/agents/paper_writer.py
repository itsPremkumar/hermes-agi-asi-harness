"""
Paper Writer Agent

Generates a LaTeX research paper draft from the collected findings,
hypotheses, and experiment designs. Includes proper citations and
bibliography generation.
"""

from __future__ import annotations

import json

from deepresearch.config import ResearchConfig
from deepresearch.providers.llm import call_llm
from deepresearch.state import (
    ExperimentDesign,
    Hypothesis,
    PaperDraft,
    PaperMetadata,
    PipelineStage,
    ResearchState,
    AgentRole,
    PaperSummary,
)


class PaperWriter:
    """Agent that writes research paper drafts in LaTeX."""

    def __init__(self, config: ResearchConfig | None = None):
        self.config = config or ResearchConfig()

    def _format_references(self, papers: list[PaperMetadata]) -> list[PaperMetadata]:
        """Format paper metadata for bibliography."""
        refs = []
        for p in papers:
            ref: PaperMetadata = {
                "arxiv_id": p.get("arxiv_id", ""),
                "pubmed_id": p.get("pubmed_id", ""),
                "title": p.get("title", ""),
                "authors": p.get("authors", []),
                "year": p.get("year", 0),
                "venue": p.get("venue", ""),
                "doi": p.get("doi", ""),
                "url": p.get("url", ""),
            }
            refs.append(ref)
        return refs

    def _build_bibliography(self, papers: list[PaperMetadata]) -> str:
        """Build a BibTeX bibliography string."""
        entries = []
        for i, p in enumerate(papers):
            authors = " and ".join(p.get("authors", ["Unknown"]) or ["Unknown"])
            title = p.get("title", "Untitled")
            year = p.get("year", 2025)
            venue = p.get("venue", "")
            key = f"paper{i}"

            if p.get("arxiv_id"):
                entries.append(
                    f"@article{{{key},\n"
                    f"  author = {{{authors}}},\n"
                    f"  title = {{{title}}},\n"
                    f"  journal = {{arXiv preprint}},\n"
                    f"  year = {{{year}}},\n"
                    f"  eprint = {{{p.get('arxiv_id')}}},\n"
                    f"}}"
                )
            elif p.get("pubmed_id"):
                entries.append(
                    f"@article{{{key},\n"
                    f"  author = {{{authors}}},\n"
                    f"  title = {{{title}}},\n"
                    f"  journal = {{{venue or 'PubMed'}}},\n"
                    f"  year = {{{year}}},\n"
                    f"  pmid = {{{p.get('pubmed_id')}}},\n"
                    f"}}"
                )
            else:
                entries.append(
                    f"@article{{{key},\n"
                    f"  author = {{{authors}}},\n"
                    f"  title = {{{title}}},\n"
                    f"  year = {{{year}}},\n"
                    f"}}"
                )
        return "\n\n".join(entries)

    def _build_abstract(
        self,
        query: str,
        hypotheses: list[Hypothesis],
        experiments: list[ExperimentDesign],
    ) -> str:
        """Generate the abstract section."""
        prompt = (
            f"Write a concise academic abstract (150-250 words) for a research "
            f"paper on the topic: '{query}'. "
            f"The paper proposes {len(hypotheses)} novel hypothesis/hypotheses "
            f"and designs {len(experiments)} experiment(s) to test them. "
            f"The research uses an autonomous multi-agent pipeline to search, "
            f"synthesize, and validate findings from the academic literature."
        )

        try:
            return call_llm(
                model=self.config.paper_model,
                prompt=prompt,
                max_tokens=300,
                temperature=0.5,
            ).strip()
        except Exception:
            return (
                f"This paper presents an autonomous research pipeline that "
                f"investigates '{query}'. We identify {len(hypotheses)} novel "
                f"research hypotheses through counterfactual reasoning and "
                f"design {len(experiments)} experiments to validate them. "
                f"Our approach demonstrates the potential for AI-driven "
                f"scientific discovery."
            )

    def write(self, state: ResearchState) -> PaperDraft:
        """Generate a full LaTeX paper draft."""
        query = state["query"]
        papers = state.get("papers", [])
        summaries = state.get("summaries", [])
        hypotheses = state.get("hypotheses", [])
        experiments = state.get("experiments", [])

        # Generate abstract
        abstract = self._build_abstract(query, hypotheses, experiments)

        # Build sections
        sections: dict[str, str] = {}

        # Introduction
        sections["Introduction"] = (
            "\\section{Introduction}\n"
            f"This paper addresses the research question: \\textit{{{query}}}. "
            f"Using an autonomous multi-agent research pipeline, we searched "
            f"the academic literature, synthesized findings from "
            f"{len(summaries)} papers, generated "
            f"{len(hypotheses)} novel hypotheses, and designed "
            f"{len(experiments)} experiment(s) to validate our proposed work.\n"
        )

        # Literature Review
        sections["Literature Review"] = "\\section{Literature Review}\n"
        for s in summaries:
            sections["Literature Review"] += (
                f"\\subsection{{{s['title']}}}\n"
                f"Key findings: {', '.join(s.get('key_findings', []))}\n"
                f"Methodology: {s.get('methodology', '')}\n"
            )

        # Hypotheses
        sections["Research Hypotheses"] = "\\section{Research Hypotheses}\n"
        for h in hypotheses:
            sections["Research Hypotheses"] += (
                f"\\paragraph{{Hypothesis {h['id']}}}: {h['statement']}\n"
                f"\\emph{{Rationale}}: {h['rationale']}\n"
                f"\\emph{{Counterfactual basis}}: {h['counterfactual_basis']}\n"
                f"Novelty score: {h['novelty_score']}\n"
            )

        # Experiment Design
        sections["Experiment Design"] = "\\section{Experiment Design}\n"
        for exp in experiments:
            sections["Experiment Design"] += (
                f"\\subsection{{{exp['experiment_type']}: {exp['description']}}}\n"
                f"\\textbf{{Methodology}}: {exp['methodology']}\n\n"
                f"\\textbf{{Resources}}: {', '.join(exp['required_resources'])}\n\n"
                f"\\textbf{{Timeline}}: {exp['estimated_timeline']}\n\n"
                f"\\textbf{{Simulated outcome}}: {exp['simulated_outcome']}\n\n"
                f"\\textbf{{Confidence intervals}}: {json.dumps(exp['confidence_intervals'])}\n"
            )

        # Results (simulated)
        sections["Results"] = "\\section{Results}\n"
        sections["Results"] += (
            "Simulated results based on the experiment designs indicate "
            "promising support for the proposed hypotheses. "
            "Detailed results are provided in the experiment sections above.\n"
        )

        # Discussion
        sections["Discussion"] = "\\section{Discussion}\n"
        sections["Discussion"] += (
            "The autonomous pipeline successfully identified research gaps, "
            "generated novel hypotheses, and designed experiments to test them. "
            "Future work includes implementing the proposed experiments and "
            "extending the pipeline to additional domains.\n"
        )

        # Bibliography
        bibliography_tex = self._build_bibliography(papers)

        return PaperDraft(
            id=f"draft_{hash(query) % 10000:04d}",
            title=f"Autonomous Research on: {query}",
            abstract=abstract,
            sections=sections,
            references=self._format_references(papers),
            hypotheses=hypotheses,
            experiment=experiments[0] if experiments else None,
            bibliography_tex=bibliography_tex,
        )

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the paper writing phase."""
        state["current_agent"] = AgentRole.WRITER

        draft = self.write(state)
        state["drafts"].append(draft)
        state["stage"] = PipelineStage.WRITE

        return state
