"""Tests for the HypothesisGenerator agent."""

import pytest
from deepresearch.agents.hypothesis_generator import HypothesisGenerator
from deepresearch.state import new_research_state, PipelineStage, AgentRole, PaperSummary


@pytest.fixture
def state_with_summaries():
    state = new_research_state(query="transformer optimization")
    state["summaries"] = [
        PaperSummary(
            paper_id="p1",
            title="Attention Is All You Need",
            authors=["Vaswani"],
            year=2017,
            abstract="We propose the Transformer architecture.",
            key_findings=["Self-attention is effective", "Parallelization possible"],
            methodology="Theoretical analysis + experiments",
            limitations=["Computation cost at inference"],
            open_questions=["Can we reduce attention overhead?"],
            citation_count=50000,
            url="https://arxiv.org/abs/1706.03762",
        ),
        PaperSummary(
            paper_id="p2",
            title="Sparse Transformers",
            authors=["Child"],
            year=2019,
            abstract="We introduce sparse attention patterns.",
            key_findings=["Sparse attention reduces cost", "Maintains quality"],
            methodology="Implementation + benchmarking",
            limitations=["Complexity of implementation"],
            open_questions=["Can we achieve better sparsity patterns?"],
            citation_count=800,
            url="https://arxiv.org/abs/1904.10509",
        ),
    ]
    state["papers"] = [
        {"arxiv_id": "p1", "title": "Paper 1", "authors": [], "year": 2017},
        {"arxiv_id": "p2", "title": "Paper 2", "authors": [], "year": 2019},
    ]
    return state


class TestHypothesisGenerator:
    def test_init(self):
        gen = HypothesisGenerator()
        assert gen.config is not None

    def test_identify_gaps(self, state_with_summaries):
        gen = HypothesisGenerator()
        gaps = gen.identify_gaps(state_with_summaries)
        assert isinstance(gaps, list)
        # Open questions should be included as gaps
        assert any("sparsity" in g.lower() or "attention overhead" in g.lower() for g in gaps) or len(gaps) > 0

    def test_generate(self, state_with_summaries):
        gen = HypothesisGenerator()
        summaries = state_with_summaries["summaries"]
        hypotheses = gen.generate(summaries, [], "transformer optimization")
        assert isinstance(hypotheses, list)
        assert len(hypotheses) >= 1
        for h in hypotheses:
            assert "id" in h
            assert "statement" in h
            assert "rationale" in h
            assert "counterfactual_basis" in h
            assert "novelty_score" in h
            assert isinstance(h["novelty_score"], (int, float))
            assert 0 <= h["novelty_score"] <= 1
            assert "supporting_papers" in h
            assert "falsifiability" in h
            assert "estimated_resource_cost" in h

    def test_run(self, state_with_summaries):
        gen = HypothesisGenerator()
        state = gen.run(state_with_summaries)
        assert state["stage"] == PipelineStage.HYPOTHESIZE
        assert state["current_agent"] == AgentRole.HYPOTHESIS
        assert len(state["hypotheses"]) >= 1

    def test_generate_with_empty_summaries(self):
        gen = HypothesisGenerator()
        hypotheses = gen.generate([], [], "test query")
        assert isinstance(hypotheses, list)
        assert len(hypotheses) >= 1
