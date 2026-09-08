"""Tests for the LiteratureReviewer agent."""

import pytest
from deepresearch.agents.literature_reviewer import LiteratureReviewer
from deepresearch.state import new_research_state, PipelineStage, AgentRole


class TestLiteratureReviewer:
    def test_init(self):
        reviewer = LiteratureReviewer()
        assert reviewer.config is not None

    def test_search_combines_sources(self):
        reviewer = LiteratureReviewer()
        papers = reviewer.search("quantum computing")
        assert len(papers) > 0
        assert all("arxiv_id" in p or "pubmed_id" in p for p in papers)

    def test_summarize(self):
        reviewer = LiteratureReviewer()
        paper = {
            "arxiv_id": "test123",
            "title": "Test Paper",
            "authors": ["Alice", "Bob"],
            "abstract": "A test abstract about testing.",
            "year": 2025,
            "venue": "ArXiv",
            "citations": 42,
            "url": "https://arxiv.org/abs/test123",
        }
        summary = reviewer.summarize(paper)
        assert summary["paper_id"] == "test123"
        assert summary["title"] == "Test Paper"
        assert summary["authors"] == ["Alice", "Bob"]
        assert isinstance(summary["key_findings"], list)
        assert isinstance(summary["methodology"], str)
        assert isinstance(summary["limitations"], list)
        assert isinstance(summary["open_questions"], list)

    def test_run(self):
        reviewer = LiteratureReviewer()
        state = new_research_state(query="machine learning")
        state = reviewer.run(state)
        assert state["stage"] == PipelineStage.SYNTHESIZE
        assert state["current_agent"] == AgentRole.LITERATURE
        assert len(state["papers"]) > 0
        assert len(state["summaries"]) > 0
        assert len(state["citations_read"]) > 0
        assert "citation_graph" in state
