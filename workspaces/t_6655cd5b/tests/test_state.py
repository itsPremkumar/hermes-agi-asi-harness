"""Tests for deepresearch state and configuration."""

import pytest
from deepresearch.state import (
    new_research_state,
    PipelineStage,
    AgentRole,
    PaperMetadata,
    PaperSummary,
    Hypothesis,
    ExperimentDesign,
    PaperDraft,
    EvaluationResult,
)
from deepresearch.config import ResearchConfig, DEFAULT_CONFIG


class TestResearchState:
    def test_new_state_defaults(self):
        state = new_research_state(query="quantum computing")
        assert state["query"] == "quantum computing"
        assert state["stage"] == PipelineStage.SEARCH
        assert state["papers"] == []
        assert state["summaries"] == []
        assert state["hypotheses"] == []
        assert state["experiments"] == []
        assert state["drafts"] == []
        assert state["evaluations"] == []
        assert state["citations_read"] == []
        assert state["citation_graph"] == {}
        assert state["error"] is None
        assert state["run_id"] != ""

    def test_new_state_with_run_id(self):
        state = new_research_state(query="test", run_id="my-run-id")
        assert state["run_id"] == "my-run-id"

    def test_state_has_timestamps(self):
        import time
        state = new_research_state(query="test")
        assert state["created_at"] <= time.time()
        assert state["updated_at"] <= time.time()

    def test_pipeline_stages(self):
        assert PipelineStage.SEARCH.value == "search"
        assert PipelineStage.READ.value == "read"
        assert PipelineStage.SYNTHESIZE.value == "synthesize"
        assert PipelineStage.HYPOTHESIZE.value == "hypothesize"
        assert PipelineStage.VALIDATE.value == "validate"
        assert PipelineStage.WRITE.value == "write"
        assert PipelineStage.DONE.value == "done"

    def test_agent_roles(self):
        assert AgentRole.LITERATURE.value == "literature_reviewer"
        assert AgentRole.HYPOTHESIS.value == "hypothesis_generator"
        assert AgentRole.EXPERIMENT.value == "experiment_designer"
        assert AgentRole.WRITER.value == "paper_writer"


class TestTypedDicts:
    def test_paper_metadata(self):
        meta = PaperMetadata(
            arxiv_id="2106.12345",
            title="Test Paper",
            authors=["Alice", "Bob"],
            abstract="A test abstract.",
            year=2025,
            venue="ArXiv",
            doi="",
            citations=42,
            references=[],
            url="https://arxiv.org/abs/2106.12345",
        )
        assert meta["title"] == "Test Paper"
        assert meta["authors"] == ["Alice", "Bob"]

    def test_paper_summary(self):
        summary = PaperSummary(
            paper_id="2106.12345",
            title="Test Paper",
            authors=["Alice"],
            year=2025,
            abstract="Abstract",
            key_findings=["Finding 1", "Finding 2"],
            methodology="Experiment",
            limitations=["Small N"],
            open_questions=["Question 1"],
            citation_count=10,
            url="https://arxiv.org/abs/2106.12345",
        )
        assert summary["key_findings"] == ["Finding 1", "Finding 2"]

    def test_hypothesis(self):
        hyp = Hypothesis(
            id="hyp_0_0001",
            statement="Test hypothesis",
            rationale="Based on evidence",
            counterfactual_basis="If X were false, then...",
            novelty_score=0.85,
            supporting_papers=["paper_1"],
            falsifiability=True,
            estimated_resource_cost="moderate",
        )
        assert hyp["novelty_score"] == 0.85
        assert hyp["falsifiability"] is True

    def test_experiment_design(self):
        exp = ExperimentDesign(
            id="exp_0001",
            hypothesis_id="hyp_0_0001",
            experiment_type="simulation",
            description="A test experiment",
            methodology="Run simulation",
            required_resources=["cluster"],
            estimated_timeline="2 weeks",
            simulated_outcome="Hypothesis supported",
            confidence_intervals={"effect_size": 0.85},
        )
        assert exp["experiment_type"] == "simulation"

    def test_paper_draft(self):
        draft = PaperDraft(
            id="draft_0001",
            title="Test Paper Draft",
            abstract="Test abstract",
            sections={"Introduction": "..."},
            references=[],
            hypotheses=[],
            experiment=None,
            bibliography_tex="@article{test}",
        )
        assert draft["title"] == "Test Paper Draft"

    def test_evaluation_result(self):
        ev = EvaluationResult(
            hypothesis_novelty=0.8,
            experiment_feasibility=0.9,
            paper_quality=0.7,
            overall_score=0.8,
            feedback=["Good work"],
            recommendations=["Improve abstract"],
        )
        assert ev["overall_score"] == 0.8


class TestConfig:
    def test_default_config(self):
        config = ResearchConfig()
        assert config.arxiv_max_results == 15
        assert config.pubmed_max_results == 15
        assert config.max_retries == 3

    def test_default_config_instance(self):
        assert DEFAULT_CONFIG is not None
        assert isinstance(DEFAULT_CONFIG, ResearchConfig)

    def test_config_model_defaults(self):
        config = ResearchConfig()
        assert "laguna" in config.literature_model
        assert "laguna" in config.hypothesis_model
