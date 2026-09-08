"""Tests for the QualityEvaluator."""

import pytest
from deepresearch.evaluation.quality_evaluator import QualityEvaluator
from deepresearch.state import (
    new_research_state,
    Hypothesis,
    ExperimentDesign,
    PaperDraft,
    EvaluationResult,
)


@pytest.fixture
def evaluator():
    return QualityEvaluator()


@pytest.fixture
def strong_hypothesis():
    return Hypothesis(
        id="hyp_0",
        statement="This is a detailed and testable hypothesis statement.",
        rationale="Based on extensive evidence and prior work in the field showing X.",
        counterfactual_basis="If X were not true, we would observe Y instead of Z.",
        novelty_score=0.9,
        supporting_papers=["paper_1", "paper_2"],
        falsifiability=True,
        estimated_resource_cost="moderate",
    )


@pytest.fixture
def weak_hypothesis():
    return Hypothesis(
        id="hyp_weak",
        statement="Maybe something happens.",
        rationale="It seems so.",
        counterfactual_basis="If not this, then maybe other?",
        novelty_score=0.1,
        supporting_papers=[],
        falsifiability=False,
        estimated_resource_cost="low",
    )


@pytest.fixture
def strong_experiment():
    return ExperimentDesign(
        id="exp_0",
        hypothesis_id="hyp_0",
        experiment_type="simulation",
        description="A detailed computational experiment to test the hypothesis.",
        methodology="Step 1: Set up simulation. Step 2: Run parameter sweep. Step 3: Analyze results.",
        required_resources=["compute_cluster", "simulation_software"],
        estimated_timeline="2-4 weeks",
        simulated_outcome="The hypothesis is supported under most conditions.",
        confidence_intervals={"effect_size": 0.85, "p_value": 0.03},
    )


@pytest.fixture
def strong_paper():
    return PaperDraft(
        id="draft_0",
        title="A Comprehensive Study of Research Methodology",
        abstract="This paper presents a comprehensive study of research methodology in the field of autonomous agents. We identify key challenges and propose novel solutions.",
        sections={
            "Introduction": "Introduction content...",
            "Literature Review": "Literature review content...",
            "Research Hypotheses": "Hypotheses content...",
            "Experiment Design": "Experiment content...",
            "Results": "Results content...",
            "Discussion": "Discussion content...",
        },
        references=[],
        hypotheses=[],
        experiment=None,
        bibliography_tex="@article{test, author={Test}}",
    )


class TestQualityEvaluator:
    def test_init(self, evaluator):
        assert evaluator.config is not None

    def test_evaluate_hypothesis_strong(self, evaluator, strong_hypothesis):
        score = evaluator.evaluate_hypothesis(strong_hypothesis)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Strong hypothesis should score well

    def test_evaluate_hypothesis_weak(self, evaluator, weak_hypothesis):
        score = evaluator.evaluate_hypothesis(weak_hypothesis)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Weak hypothesis should score low

    def test_evaluate_experiment_strong(self, evaluator, strong_experiment):
        score = evaluator.evaluate_experiment(strong_experiment)
        assert 0.0 <= score <= 1.0
        assert score > 0.5

    def test_evaluate_paper_strong(self, evaluator, strong_paper):
        score = evaluator.evaluate_paper(strong_paper)
        assert 0.0 <= score <= 1.0
        assert score > 0.5

    def test_evaluate_paper_missing_sections(self, evaluator):
        draft = PaperDraft(
            id="draft_weak",
            title="Short Title",
            abstract="Short.",  # Too short
            sections={"Introduction": "A"},  # Missing sections
            references=[],
            hypotheses=[],
            experiment=None,
            bibliography_tex="",
        )
        score = evaluator.evaluate_paper(draft)
        assert 0.0 <= score <= 1.0
        assert score < 0.7  # Should be low

    def test_evaluate_full_state(self, evaluator, strong_hypothesis, strong_experiment, strong_paper):
        state = new_research_state(query="test query")
        state["hypotheses"] = [strong_hypothesis]
        state["experiments"] = [strong_experiment]
        state["drafts"] = [strong_paper]
        result = evaluator.evaluate(state)
        assert isinstance(result, dict)
        assert "hypothesis_novelty" in result
        assert 0.0 <= result["hypothesis_novelty"] <= 1.0
        assert 0.0 <= result["experiment_feasibility"] <= 1.0
        assert 0.0 <= result["paper_quality"] <= 1.0
        assert 0.0 <= result["overall_score"] <= 1.0
        assert isinstance(result["feedback"], list)
        assert isinstance(result["recommendations"], list)

    def test_evaluate_empty_state(self, evaluator):
        state = new_research_state(query="test")
        result = evaluator.evaluate(state)
        assert result["hypothesis_novelty"] == 0.0
        assert result["experiment_feasibility"] == 0.0
        assert result["paper_quality"] == 0.0
        assert result["overall_score"] == 0.0
        assert len(result["feedback"]) >= 3
        assert len(result["recommendations"]) >= 3
