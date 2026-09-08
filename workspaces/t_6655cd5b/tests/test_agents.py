"""Tests for deepresearch.agents."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from deepresearch.agents.literature_reviewer import LiteratureReviewer
from deepresearch.agents.hypothesis_generator import HypothesisGenerator
from deepresearch.agents.experiment_designer import ExperimentDesigner
from deepresearch.agents.paper_writer import PaperWriter
from deepresearch.agents.pipeline import ResearchPipeline
from deepresearch.config import ResearchConfig
from deepresearch.state import (
    new_research_state,
    PipelineStage,
    AgentRole,
    PaperMetadata,
    PaperSummary,
    Hypothesis,
    ExperimentDesign,
    PaperDraft,
)
from deepresearch.tools.arxiv_api import ArxivAPI
from deepresearch.tools.pubmed_api import PubMedAPI
from deepresearch.tools.citation_graph import CitationGraphAnalyzer


class TestLiteratureReviewer:
    """Tests for LiteratureReviewer agent."""

    def test_init(self):
        """Test initialization."""
        config = ResearchConfig()
        agent = LiteratureReviewer(config)
        assert agent.config == config
        assert agent.arxiv is not None
        assert agent.pubmed is not None
        assert agent.graph_analyzer is not None

    def test_init_default_config(self):
        """Test initialization with default config."""
        agent = LiteratureReviewer()
        assert agent.config is not None

    def test_search_returns_results(self):
        """Test search returns paper metadata."""
        config = ResearchConfig()
        agent = LiteratureReviewer(config)
        # Mock the arxiv and pubmed search to avoid network calls
        with patch.object(agent.arxiv, "search", return_value=[
            {"arxiv_id": "test.123", "title": "Test Paper", "authors": ["Alice"], "abstract": "Test abstract", "year": 2025, "links": []}
        ]):
            with patch.object(agent.pubmed, "search", return_value=[]):
                results = agent.search("test query")
                assert len(results) > 0
                assert results[0]["title"] == "Test Paper"

    def test_summarize(self):
        """Test paper summarization."""
        config = ResearchConfig()
        agent = LiteratureReviewer(config)
        paper = {
            "arxiv_id": "test.123",
            "title": "Test Paper",
            "authors": ["Alice"],
            "abstract": "Test abstract about transformers",
            "year": 2025,
            "citations": 10,
            "links": [{"href": "https://arxiv.org/abs/test.123"}],
        }
        summary = agent.summarize(paper)
        assert summary["paper_id"] == "test.123"
        assert summary["title"] == "Test Paper"
        assert len(summary["key_findings"]) > 0

    def test_run(self):
        """Test full literature review run."""
        config = ResearchConfig()
        agent = LiteratureReviewer(config)
        state = new_research_state(query="test query", run_id="test-run")
        with patch.object(agent, "search", return_value=[
            {"arxiv_id": "test.123", "title": "Test Paper", "authors": ["Alice"], "abstract": "Test abstract", "year": 2025, "citations": 10, "references": [], "links": []}
        ]):
            result = agent.run(state)
            assert result["stage"] == PipelineStage.SYNTHESIZE
            assert result["current_agent"] == AgentRole.LITERATURE
            assert len(result["papers"]) > 0


class TestHypothesisGenerator:
    """Tests for HypothesisGenerator agent."""

    def test_init(self):
        """Test initialization."""
        config = ResearchConfig()
        agent = HypothesisGenerator(config)
        assert agent.config == config
        assert agent.graph_analyzer is not None

    def test_identify_gaps(self):
        """Test gap identification."""
        config = ResearchConfig()
        agent = HypothesisGenerator(config)
        state = new_research_state(query="test", run_id="test-run")
        state["papers"] = [
            {"arxiv_id": "p1", "title": "Paper 1", "authors": ["A"], "abstract": "Abstract", "year": 2025, "citations": 5, "references": [], "links": []},
            {"arxiv_id": "p2", "title": "Paper 2", "authors": ["B"], "abstract": "Abstract", "year": 2025, "citations": 3, "references": [], "links": []},
        ]
        state["summaries"] = [
            {"paper_id": "p1", "title": "Paper 1", "authors": ["A"], "year": 2025, "abstract": "Abstract", "key_findings": ["Finding 1"], "methodology": "Experiment", "limitations": ["Limitation 1"], "open_questions": ["Question 1"], "citation_count": 5, "url": ""},
        ]
        gaps = agent.identify_gaps(state)
        assert isinstance(gaps, list)

    def test_generate(self):
        """Test hypothesis generation."""
        config = ResearchConfig()
        agent = HypothesisGenerator(config)
        summaries = [
            {"paper_id": "p1", "title": "Paper 1", "authors": ["A"], "year": 2025, "abstract": "Abstract", "key_findings": ["Finding 1"], "methodology": "Experiment", "limitations": ["Limitation 1"], "open_questions": ["Question 1"], "citation_count": 5, "url": ""},
        ]
        gaps = ["Gap 1"]
        hypotheses = agent.generate(summaries, gaps, "test query")
        assert len(hypotheses) > 0
        assert hypotheses[0]["statement"] != ""

    def test_run(self):
        """Test full hypothesis generation run."""
        config = ResearchConfig()
        agent = HypothesisGenerator(config)
        state = new_research_state(query="test", run_id="test-run")
        state["papers"] = [
            {"arxiv_id": "p1", "title": "Paper 1", "authors": ["A"], "abstract": "Abstract", "year": 2025, "citations": 5, "references": [], "links": []},
        ]
        state["summaries"] = [
            {"paper_id": "p1", "title": "Paper 1", "authors": ["A"], "year": 2025, "abstract": "Abstract", "key_findings": ["Finding 1"], "methodology": "Experiment", "limitations": ["Limitation 1"], "open_questions": ["Question 1"], "citation_count": 5, "url": ""},
        ]
        result = agent.run(state)
        assert result["stage"] == PipelineStage.HYPOTHESIZE
        assert result["current_agent"] == AgentRole.HYPOTHESIS
        assert len(result["hypotheses"]) > 0


class TestExperimentDesigner:
    """Tests for ExperimentDesigner agent."""

    def test_init(self):
        """Test initialization."""
        config = ResearchConfig()
        agent = ExperimentDesigner(config)
        assert agent.config == config

    def test_design(self):
        """Test experiment design."""
        config = ResearchConfig()
        agent = ExperimentDesigner(config)
        hypothesis = {
            "id": "hyp_0",
            "statement": "Test hypothesis about transformers",
            "rationale": "Based on evidence",
            "counterfactual_basis": "If X were true, then Y",
            "novelty_score": 0.8,
            "supporting_papers": ["p1"],
            "falsifiability": True,
            "estimated_resource_cost": "moderate",
        }
        summaries = [
            {"paper_id": "p1", "title": "Paper 1", "authors": ["A"], "year": 2025, "abstract": "Abstract", "key_findings": ["Finding 1"], "methodology": "Experiment", "limitations": ["Limitation 1"], "open_questions": ["Question 1"], "citation_count": 5, "url": ""},
        ]
        exp = agent.design(hypothesis, summaries)
        assert exp["hypothesis_id"] == "hyp_0"
        assert exp["experiment_type"] == "simulation"
        assert len(exp["description"]) > 0

    def test_run(self):
        """Test full experiment design run."""
        config = ResearchConfig()
        agent = ExperimentDesigner(config)
        state = new_research_state(query="test", run_id="test-run")
        state["hypotheses"] = [
            {"id": "hyp_0", "statement": "Test hypothesis", "rationale": "Rationale", "counterfactual_basis": "Counterfactual", "novelty_score": 0.8, "supporting_papers": [], "falsifiability": True, "estimated_resource_cost": "moderate"},
        ]
        state["summaries"] = []
        result = agent.run(state)
        assert result["stage"] == PipelineStage.VALIDATE
        assert result["current_agent"] == AgentRole.EXPERIMENT
        assert len(result["experiments"]) > 0


class TestPaperWriter:
    """Tests for PaperWriter agent."""

    def test_init(self):
        """Test initialization."""
        config = ResearchConfig()
        agent = PaperWriter(config)
        assert agent.config == config

    def test_write(self):
        """Test paper writing."""
        config = ResearchConfig()
        agent = PaperWriter(config)
        state = new_research_state(query="test query", run_id="test-run")
        state["papers"] = [
            {"arxiv_id": "p1", "title": "Paper 1", "authors": ["Alice"], "year": 2025, "venue": "ArXiv", "doi": "", "url": "https://arxiv.org/abs/p1"},
        ]
        state["summaries"] = [
            {"paper_id": "p1", "title": "Paper 1", "authors": ["Alice"], "year": 2025, "abstract": "Abstract", "key_findings": ["Finding 1"], "methodology": "Experiment", "limitations": ["Limitation 1"], "open_questions": ["Question 1"], "citation_count": 5, "url": ""},
        ]
        state["hypotheses"] = [
            {"id": "hyp_0", "statement": "Test hypothesis", "rationale": "Rationale", "counterfactual_basis": "Counterfactual", "novelty_score": 0.8, "supporting_papers": [], "falsifiability": True, "estimated_resource_cost": "moderate"},
        ]
        state["experiments"] = [
            {"id": "exp_0", "hypothesis_id": "hyp_0", "experiment_type": "simulation", "description": "Test experiment", "methodology": "Simulation", "required_resources": ["compute"], "estimated_timeline": "2 weeks", "simulated_outcome": "Positive", "confidence_intervals": {"effect_size": 0.8}},
        ]
        draft = agent.write(state)
        assert draft["title"] != ""
        assert draft["abstract"] != ""
        assert len(draft["sections"]) > 0

    def test_run(self):
        """Test full paper writing run."""
        config = ResearchConfig()
        agent = PaperWriter(config)
        state = new_research_state(query="test query", run_id="test-run")
        state["papers"] = [
            {"arxiv_id": "p1", "title": "Paper 1", "authors": ["Alice"], "year": 2025, "venue": "ArXiv", "doi": "", "url": "https://arxiv.org/abs/p1"},
        ]
        state["summaries"] = [
            {"paper_id": "p1", "title": "Paper 1", "authors": ["Alice"], "year": 2025, "abstract": "Abstract", "key_findings": ["Finding 1"], "methodology": "Experiment", "limitations": ["Limitation 1"], "open_questions": ["Question 1"], "citation_count": 5, "url": ""},
        ]
        state["hypotheses"] = [
            {"id": "hyp_0", "statement": "Test hypothesis", "rationale": "Rationale", "counterfactual_basis": "Counterfactual", "novelty_score": 0.8, "supporting_papers": [], "falsifiability": True, "estimated_resource_cost": "moderate"},
        ]
        state["experiments"] = [
            {"id": "exp_0", "hypothesis_id": "hyp_0", "experiment_type": "simulation", "description": "Test experiment", "methodology": "Simulation", "required_resources": ["compute"], "estimated_timeline": "2 weeks", "simulated_outcome": "Positive", "confidence_intervals": {"effect_size": 0.8}},
        ]
        state["drafts"] = []
        result = agent.run(state)
        assert result["stage"] == PipelineStage.WRITE
        assert result["current_agent"] == AgentRole.WRITER
        assert len(result["drafts"]) == 1


class TestResearchPipeline:
    """Tests for ResearchPipeline orchestrator."""

    def test_init(self):
        """Test initialization."""
        config = ResearchConfig()
        pipeline = ResearchPipeline(config)
        assert pipeline.config == config
        assert pipeline.literature is not None
        assert pipeline.hypothesis is not None
        assert pipeline.experiments is not None
        assert pipeline.writer is not None
        assert pipeline.memory is not None
        assert pipeline.evaluator is not None

    def test_run(self):
        """Test full pipeline run."""
        config = ResearchConfig()
        pipeline = ResearchPipeline(config)
        state = pipeline.run("quantum computing applications")
        assert state["query"] == "quantum computing applications"
        assert state["stage"] == PipelineStage.DONE
        assert len(state["papers"]) > 0
        assert len(state["summaries"]) > 0
        assert len(state["hypotheses"]) > 0
        assert len(state["experiments"]) > 0
        assert len(state["drafts"]) > 0
        assert len(state["evaluations"]) > 0

    def test_get_paper_latex(self):
        """Test LaTeX generation."""
        config = ResearchConfig()
        pipeline = ResearchPipeline(config)
        state = pipeline.run("test query")
        latex = pipeline.get_paper_latex(state)
        assert r"\documentclass" in latex
        assert r"\begin{document}" in latex
        assert r"\end{document}" in latex
