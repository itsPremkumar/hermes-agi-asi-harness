"""Tests for the PaperWriter agent."""

import pytest
from deepresearch.agents.paper_writer import PaperWriter
from deepresearch.state import (
    new_research_state,
    PipelineStage,
    AgentRole,
    PaperDraft,
    PaperMetadata,
    Hypothesis,
    ExperimentDesign,
)


@pytest.fixture
def completed_state():
    state = new_research_state(query="sparse attention mechanisms")
    state["papers"] = [
        PaperMetadata(
            arxiv_id="p1",
            title="Attention Is All You Need",
            authors=["Vaswani"],
            abstract="Transformer architecture.",
            year=2017,
            venue="ArXiv",
            doi="",
            citations=50000,
            references=[],
            url="https://arxiv.org/abs/1706.03762",
        ),
        PaperMetadata(
            arxiv_id="p2",
            title="Sparse Transformers",
            authors=["Child"],
            year=2019,
            venue="ArXiv",
            abstract="Sparse patterns.",
            doi="",
            citations=800,
            references=[],
            url="",
        ),
    ]
    state["summaries"] = []
    state["hypotheses"] = [
        Hypothesis(
            id="h1", statement="Sparse attention reduces cost", rationale="Evidence",
            counterfactual_basis="If-then", novelty_score=0.85,
            supporting_papers=["p1"], falsifiability=True,
            estimated_resource_cost="moderate",
        )
    ]
    state["experiments"] = [
        ExperimentDesign(
            id="e1", hypothesis_id="h1",
            experiment_type="simulation",
            description="Sim test", methodology="Method",
            required_resources=["cluster"],
            estimated_timeline="2 weeks",
            simulated_outcome="Supported",
            confidence_intervals={"effect_size": 0.85},
        )
    ]
    return state


class TestPaperWriter:
    def test_init(self):
        writer = PaperWriter()
        assert writer.config is not None

    def test_build_bibliography(self, completed_state):
        writer = PaperWriter()
        bib = writer._build_bibliography(completed_state["papers"])
        assert "@article" in bib
        assert "Vaswani" in bib

    def test_build_abstract(self, completed_state):
        writer = PaperWriter()
        abstract = writer._build_abstract(
            completed_state["query"],
            completed_state["hypotheses"],
            completed_state["experiments"],
        )
        assert isinstance(abstract, str)
        assert len(abstract) > 0

    def test_write(self, completed_state):
        writer = PaperWriter()
        draft = writer.write(completed_state)
        assert draft["title"] != ""
        assert draft["abstract"] != ""
        assert "Introduction" in draft["sections"]
        assert "Literature Review" in draft["sections"]
        assert "Research Hypotheses" in draft["sections"]
        assert "Experiment Design" in draft["sections"]
        assert len(draft["bibliography_tex"]) > 0
        assert len(draft["references"]) == 2

    def test_run(self, completed_state):
        writer = PaperWriter()
        state = writer.run(completed_state)
        assert state["stage"] == PipelineStage.WRITE
        assert state["current_agent"] == AgentRole.WRITER
        assert len(state["drafts"]) == 1
        assert state["drafts"][0]["title"] != ""

    def test_format_references(self, completed_state):
        writer = PaperWriter()
        refs = writer._format_references(completed_state["papers"])
        assert len(refs) == 2
        assert all("arxiv_id" in r for r in refs)
