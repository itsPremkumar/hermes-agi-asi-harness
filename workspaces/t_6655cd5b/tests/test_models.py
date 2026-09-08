"""Tests for deepresearch.models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from deepresearch.models import (
    AgentType,
    Citation,
    ExperimentDesign,
    Hypothesis,
    Paper,
    PaperStatus,
    ResearchPlan,
    ResearchStage,
    Source,
    SynthesisResult,
)


class TestPaper:
    """Tests for the Paper model."""

    def test_paper_creation(self):
        """Test basic paper creation."""
        paper = Paper(
            id="2101.00123",
            title="Attention Is All You Need",
            authors=["Vaswani", "Bahdanau"],
            abstract="We propose a new architecture...",
            year=2017,
            source=Source.ARXIV,
            url="https://arxiv.org/abs/2101.00123",
            keywords=["transformers", "attention"],
        )
        assert paper.id == "2101.00123"
        assert paper.title == "Attention Is All You Need"
        assert paper.authors == ["Vaswani", "Bahdanau"]
        assert paper.year == 2017
        assert paper.source == Source.ARXIV
        assert paper.status == PaperStatus.PENDING

    def test_paper_defaults(self):
        """Test paper default values."""
        paper = Paper(id="test", title="Test Paper")
        assert paper.authors == []
        assert paper.abstract == ""
        assert paper.year == 2024
        assert paper.source == Source.ARXIV
        assert paper.keywords == []
        assert paper.references == []
        assert paper.status == PaperStatus.PENDING
        assert paper.content is None
        assert paper.embedding is None

    def test_paper_cite(self):
        """Test citation formatting."""
        paper = Paper(
            id="test",
            title="A Study on Deep Learning",
            authors=["Smith", "Johnson", "Williams", "Brown"],
            year=2020,
            source=Source.ARXIV,
        )
        citation = paper.cite()
        assert "Smith, Johnson, Williams et al." in citation
        assert "(2020)" in citation
        assert "A Study on Deep Learning" in citation

    def test_paper_cite_single_author(self):
        """Test citation with single author."""
        paper = Paper(
            id="test",
            title="A Study",
            authors=["Smith"],
            year=2020,
            source=Source.ARXIV,
        )
        citation = paper.cite()
        assert "Smith" in citation
        assert "et al" not in citation

    def test_paper_model_dump(self):
        """Test model_dump excludes None values properly."""
        paper = Paper(id="test", title="Test")
        data = paper.model_dump()
        assert "embedding" in data
        assert data["embedding"] is None


class TestHypothesis:
    """Tests for the Hypothesis model."""

    def test_hypothesis_creation(self):
        """Test basic hypothesis creation."""
        hyp = Hypothesis(
            id="hyp-1",
            statement="Increased attention heads improve model performance",
            confidence=0.85,
            supporting_papers=["paper1", "paper2"],
            gap_description="Limited work on head count optimization",
            novelty_score=0.7,
        )
        assert hyp.id == "hyp-1"
        assert hyp.confidence == 0.85
        assert len(hyp.supporting_papers) == 2
        assert hyp.novelty_score == 0.7

    def test_hypothesis_confidence_bounds(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Hypothesis(id="test", statement="test", confidence=1.5)
        with pytest.raises(ValidationError):
            Hypothesis(id="test", statement="test", confidence=-0.1)

    def test_hypothesis_novelty_bounds(self):
        """Test novelty_score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Hypothesis(
                id="test", statement="test", novelty_score=1.5
            )
        with pytest.raises(ValidationError):
            Hypothesis(
                id="test", statement="test", novelty_score=-0.5
            )

    def test_hypothesis_defaults(self):
        """Test hypothesis default values."""
        hyp = Hypothesis(id="test", statement="A hypothesis", confidence=0.5)
        assert hyp.confidence == 0.5
        assert hyp.supporting_papers == []
        assert hyp.contradicting_papers == []
        assert hyp.gap_description == ""
        assert hyp.novelty_score == 0.0

    def test_hypothesis_to_prompt(self):
        """Test hypothesis prompt formatting."""
        hyp = Hypothesis(
            id="test",
            statement="Test hypothesis",
            confidence=0.8,
            supporting_papers=["p1", "p2", "p3"],
            contradicting_papers=["p4"],
            gap_description="Gap description",
            novelty_score=0.6,
        )
        prompt = hyp.to_prompt()
        assert "Test hypothesis" in prompt
        assert "Confidence: 0.80" in prompt
        assert "Novelty: 0.60" in prompt
        assert "Gap: Gap description" in prompt
        assert "Supporting: 3 papers" in prompt
        assert "contradicting: 1 papers" in prompt.lower()


class TestExperimentDesign:
    """Tests for the ExperimentDesign model."""

    def test_experiment_creation(self):
        """Test basic experiment creation."""
        exp = ExperimentDesign(
            id="exp-1",
            hypothesis_id="hyp-1",
            title="Testing Attention Head Count",
            description="Experiment to test hypothesis about attention heads",
            methodology="Controlled experiment with varying head counts",
            variables=["num_heads", "model_size", "dataset"],
            expected_outcome="Models with 16 heads will outperform 8 heads",
            feasibility_score=0.9,
            simulation_code="print('hello')",
        )
        assert exp.id == "exp-1"
        assert exp.hypothesis_id == "hyp-1"
        assert exp.feasibility_score == 0.9
        assert exp.simulation_code is not None

    def test_experiment_feasibility_bounds(self):
        """Test feasibility_score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            ExperimentDesign(
                id="test", hypothesis_id="h1", title="T",
                description="D", methodology="M",
                feasibility_score=1.5
            )
        with pytest.raises(ValidationError):
            ExperimentDesign(
                id="test", hypothesis_id="h1", title="T",
                description="D", methodology="M",
                feasibility_score=-0.1
            )

    def test_experiment_to_markdown(self):
        """Test experiment markdown rendering."""
        exp = ExperimentDesign(
            id="exp-1",
            hypothesis_id="hyp-1",
            title="Test Experiment",
            description="Test description",
            methodology="Test methodology",
            variables=["var1", "var2"],
            expected_outcome="Test outcome",
            feasibility_score=0.75,
        )
        md = exp.to_markdown()
        assert "## Test Experiment" in md
        assert "**Description:** Test description" in md
        assert "**Methodology:** Test methodology" in md
        assert "**Variables:** var1, var2" in md
        assert "**Expected Outcome:** Test outcome" in md
        assert "**Feasibility:** 0.75" in md


class TestSynthesisResult:
    """Tests for the SynthesisResult model."""

    def test_synthesis_defaults(self):
        """Test synthesis result defaults."""
        result = SynthesisResult()
        assert result.themes == []
        assert result.key_findings == []
        assert result.contradictions == []
        assert result.knowledge_gaps == []
        assert result.citation_network_insights == []

    def test_synthesis_with_data(self):
        """Test synthesis result with data."""
        result = SynthesisResult(
            themes=["transformers", "attention"],
            key_findings=["Finding 1", "Finding 2"],
            contradictions=["Contradiction 1"],
            knowledge_gaps=["Gap 1", "Gap 2"],
            citation_network_insights=["Insight 1"],
        )
        assert len(result.themes) == 2
        assert len(result.key_findings) == 2


class TestResearchPlan:
    """Tests for the ResearchPlan model."""

    def test_plan_creation(self):
        """Test basic plan creation."""
        plan = ResearchPlan(query="transformer architectures")
        assert plan.query == "transformer architectures"
        assert plan.stage == ResearchStage.SEARCH
        assert plan.papers == []
        assert plan.hypotheses == []
        assert plan.experiments == []
        assert plan.synthesis is None
        assert plan.final_paper is None

    def test_plan_progress_empty(self):
        """Test progress of empty plan."""
        plan = ResearchPlan(query="test")
        progress = plan.progress
        assert progress["papers_count"] == 0
        assert progress["hypotheses_count"] == 0
        assert progress["experiments_count"] == 0
        assert progress["stage"] == "search"
        assert progress["has_synthesis"] is False
        assert progress["has_paper"] is False

    def test_plan_progress_with_data(self):
        """Test progress with populated plan."""
        plan = ResearchPlan(query="test")
        plan.stage = ResearchStage.COMPLETE
        plan.papers = [Paper(id="1", title="T1")]
        plan.hypotheses = [Hypothesis(id="h1", statement="H1", confidence=0.5)]
        plan.experiments = [ExperimentDesign(
            id="e1", hypothesis_id="h1", title="E", description="D", methodology="M",
            expected_outcome="Expected outcome"
        )]
        plan.synthesis = SynthesisResult(themes=["t1"])
        plan.final_paper = "LaTeX content"

        progress = plan.progress
        assert progress["papers_count"] == 1
        assert progress["hypotheses_count"] == 1
        assert progress["experiments_count"] == 1
        assert progress["stage"] == "complete"
        assert progress["has_synthesis"] is True
        assert progress["has_paper"] is True


class TestEnums:
    """Tests for model enums."""

    def test_agent_type_values(self):
        """Test AgentType enum values."""
        assert AgentType.LITERATURE_REVIEWER.value == "literature_reviewer"
        assert AgentType.HYPOTHESIS_GENERATOR.value == "hypothesis_generator"
        assert AgentType.EXPERIMENT_DESIGNER.value == "experiment_designer"
        assert AgentType.PAPER_WRITER.value == "paper_writer"

    def test_research_stage_values(self):
        """Test ResearchStage enum values."""
        assert ResearchStage.SEARCH.value == "search"
        assert ResearchStage.READ.value == "read"
        assert ResearchStage.SYNTHESIZE.value == "synthesize"
        assert ResearchStage.HYPOTHESIZE.value == "hypothesize"
        assert ResearchStage.VALIDATE.value == "validate"
        assert ResearchStage.WRITE.value == "write"
        assert ResearchStage.COMPLETE.value == "complete"

    def test_source_values(self):
        """Test Source enum values."""
        assert Source.ARXIV.value == "arxiv"
        assert Source.PUBMED.value == "pubmed"
        assert Source.CROSSREF.value == "crossref"

    def test_paper_status_values(self):
        """Test PaperStatus enum values."""
        assert PaperStatus.PENDING.value == "pending"
        assert PaperStatus.FETCHED.value == "fetched"
        assert PaperStatus.ANALYZED.value == "analyzed"
        assert PaperStatus.ARCHIVED.value == "archived"
