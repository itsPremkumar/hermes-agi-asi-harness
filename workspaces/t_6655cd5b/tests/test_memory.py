"""Tests for ResearchMemory (SQLite-backed storage)."""

import os
import tempfile
import pytest
from deepresearch.memory.research_memory import ResearchMemory
from deepresearch.config import ResearchConfig
from deepresearch.state import new_research_state, PipelineStage, AgentRole


@pytest.fixture
def memory():
    """Create a memory instance with a temp database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    config = ResearchConfig()
    config.sqlite_path = db_path
    mem = ResearchMemory(config)
    yield mem
    mem.clear()
    os.unlink(db_path)


@pytest.fixture
def sample_state():
    state = new_research_state(query="test research query", run_id="test-run-001")
    state["papers"] = [{
        "arxiv_id": "test123",
        "title": "Test Paper",
        "authors": ["Alice"],
        "abstract": "Test abstract",
        "year": 2025,
        "venue": "ArXiv",
        "citations": 10,
        "references": ["ref1"],
        "url": "https://arxiv.org/abs/test123",
    }]
    state["summaries"] = [{
        "paper_id": "test123",
        "title": "Test Paper",
        "authors": ["Alice"],
        "year": 2025,
        "abstract": "Test abstract",
        "key_findings": ["Finding 1"],
        "methodology": "Experiment",
        "limitations": ["Small N"],
        "open_questions": ["Q1"],
        "citation_count": 10,
        "url": "",
    }]
    state["hypotheses"] = [{
        "id": "hyp_0",
        "statement": "Test hypothesis",
        "rationale": "Testing rationale",
        "counterfactual_basis": "If-then",
        "novelty_score": 0.85,
        "supporting_papers": ["test123"],
        "falsifiability": True,
        "estimated_resource_cost": "moderate",
    }]
    state["experiments"] = [{
        "id": "exp_0",
        "hypothesis_id": "hyp_0",
        "experiment_type": "simulation",
        "description": "Test experiment",
        "methodology": "Simulation",
        "required_resources": ["cluster"],
        "estimated_timeline": "2 weeks",
        "simulated_outcome": "Supported",
        "confidence_intervals": {"effect_size": 0.85},
    }]
    state["drafts"] = [{
        "id": "draft_0",
        "title": "Test Draft",
        "abstract": "Test abstract",
        "sections": {"Introduction": "..."},
        "references": [],
        "hypotheses": [],
        "experiment": None,
        "bibliography_tex": "@article{test}",
    }]
    state["evaluations"] = [{
        "hypothesis_novelty": 0.8,
        "experiment_feasibility": 0.9,
        "paper_quality": 0.7,
        "overall_score": 0.8,
        "feedback": ["Good"],
        "recommendations": ["Improve"],
    }]
    return state


class TestResearchMemory:
    def test_init(self, memory):
        assert memory.db_path is not None

    def test_store_state(self, memory, sample_state):
        memory.store_state(sample_state)
        # Verify it was stored
        retrieved = memory.retrieve_state("test-run-001")
        assert retrieved is not None
        assert retrieved["query"] == "test research query"
        assert len(retrieved["papers"]) == 1
        assert len(retrieved["hypotheses"]) == 1

    def test_retrieve_state_not_found(self, memory):
        result = memory.retrieve_state("nonexistent-run")
        assert result is None

    def test_list_runs(self, memory, sample_state):
        memory.store_state(sample_state)
        runs = memory.list_runs()
        assert len(runs) == 1
        assert runs[0]["run_id"] == "test-run-001"
        assert runs[0]["query"] == "test research query"

    def test_search_papers(self, memory, sample_state):
        memory.store_state(sample_state)
        results = memory.search_papers("Test Paper")
        assert len(results) == 1
        assert results[0]["title"] == "Test Paper"

    def test_search_papers_no_match(self, memory, sample_state):
        memory.store_state(sample_state)
        results = memory.search_papers("nonexistent")
        assert len(results) == 0

    def test_get_hypotheses(self, memory, sample_state):
        memory.store_state(sample_state)
        hyps = memory.get_hypotheses("test-run-001")
        assert len(hyps) == 1
        assert hyps[0]["statement"] == "Test hypothesis"

    def test_get_hypotheses_no_run(self, memory, sample_state):
        memory.store_state(sample_state)
        hyps = memory.get_hypotheses("nonexistent")
        assert len(hyps) == 0

    def test_clear(self, memory, sample_state):
        memory.store_state(sample_state)
        assert len(memory.list_runs()) == 1
        memory.clear()
        assert len(memory.list_runs()) == 0

    def test_multiple_states(self, memory):
        for i in range(3):
            state = new_research_state(query=f"query {i}", run_id=f"run-{i}")
            memory.store_state(state)
        runs = memory.list_runs()
        assert len(runs) == 3
