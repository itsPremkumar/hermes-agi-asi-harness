"""
Literature Reviewer Agent

Reads academic papers from ArXiv and PubMed, summarizes key findings,
methodologies, limitations, and open questions. Builds the citation
graph for gap detection.
"""

from __future__ import annotations

import json

from deepresearch.config import ResearchConfig
from deepresearch.providers.llm import call_llm
from deepresearch.state import (
    PaperMetadata,
    PaperSummary,
    PipelineStage,
    ResearchState,
    AgentRole,
)
from deepresearch.tools.arxiv_api import ArxivAPI
from deepresearch.tools.pubmed_api import PubMedAPI
from deepresearch.tools.citation_graph import CitationGraphAnalyzer


class LiteratureReviewer:
    """Agent that searches and reads academic papers."""

    def __init__(self, config: ResearchConfig | None = None):
        self.config = config or ResearchConfig()
        self.arxiv = ArxivAPI(email=self.config.arxiv_email, max_results=self.config.arxiv_max_results)
        self.pubmed = PubMedAPI(email=self.config.arxiv_email, max_results=self.config.pubmed_max_results)
        self.graph_analyzer = CitationGraphAnalyzer()

    def search(self, query: str) -> list[PaperMetadata]:
        """Search ArXiv and PubMed for papers matching the query."""
        combined: list[PaperMetadata] = []

        arxiv_results = self.arxiv.search(query)
        for r in arxiv_results:
            meta: PaperMetadata = {
                "arxiv_id": r.get("arxiv_id", ""),
                "title": r.get("title", ""),
                "authors": r.get("authors", []),
                "abstract": r.get("abstract", ""),
                "year": r.get("year", 0),
                "venue": "ArXiv",
                "doi": r.get("doi", ""),
                "citations": r.get("citation_count", 0),
                "references": r.get("references", []),
                "url": r.get("links", [{}])[0].get("href", "") if r.get("links") else "",
            }
            combined.append(meta)

        pubmed_results = self.pubmed.search(query)
        for r in pubmed_results:
            meta: PaperMetadata = {
                "pubmed_id": r.get("pubmed_id", ""),
                "title": r.get("title", ""),
                "authors": r.get("authors", []),
                "abstract": r.get("abstract", ""),
                "year": r.get("year", 0),
                "venue": "PubMed",
                "doi": r.get("doi", ""),
                "citations": r.get("citation_count", 0),
                "references": r.get("references", []),
                "url": r.get("links", [{}])[0].get("href", "") if r.get("links") else "",
            }
            combined.append(meta)

        return combined

    def summarize(self, paper: PaperMetadata) -> PaperSummary:
        """Summarize a single paper using the LLM."""
        prompt = (
            f"You are a literature review agent. Read the following paper and "
            f"extract: (1) key findings, (2) methodology used, (3) limitations, "
            f"and (4) open questions or research gaps this paper raises.\n\n"
            f"Title: {paper.get('title', '')}\n"
            f"Authors: {', '.join(paper.get('authors', []))}\n"
            f"Abstract: {paper.get('abstract', '')}\n"
            f"Year: {paper.get('year', '')}\n"
            f"Citations: {paper.get('citations', 0)}\n\n"
            f"Return your response as JSON with keys: "
            f"'key_findings' (list), 'methodology' (str), "
            f"'limitations' (list), 'open_questions' (list)."
        )

        try:
            raw = call_llm(
                model=self.config.literature_model,
                prompt=prompt,
                max_tokens=1024,
                temperature=0.3,
            )
            data = json.loads(raw)
        except Exception:
            data = {
                "key_findings": ["Finding from paper"],
                "methodology": "Unknown methodology",
                "limitations": ["Not specified"],
                "open_questions": ["Open question from paper"],
            }

        paper_id = paper.get("arxiv_id") or paper.get("pubmed_id") or paper.get("doi", "")
        return PaperSummary(
            paper_id=paper_id,
            title=paper.get("title", ""),
            authors=paper.get("authors", []),
            year=paper.get("year", 0),
            abstract=paper.get("abstract", ""),
            key_findings=data.get("key_findings", []),
            methodology=data.get("methodology", ""),
            limitations=data.get("limitations", []),
            open_questions=data.get("open_questions", []),
            citation_count=paper.get("citations", 0),
            url=paper.get("url", ""),
        )

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the literature review phase."""
        query = state["query"]

        # Search for papers
        papers = self.search(query)
        state["papers"] = papers
        state["current_agent"] = AgentRole.LITERATURE

        # Build citation graph
        self.graph_analyzer.build_from_papers(papers)
        state["citation_graph"] = dict(self.graph_analyzer.graph)

        # Summarize each paper
        summaries = []
        for paper in papers:
            summary = self.summarize(paper)
            summaries.append(summary)
            state["citations_read"].append(summary["paper_id"])

        state["summaries"] = summaries
        state["stage"] = PipelineStage.SYNTHESIZE

        return state
