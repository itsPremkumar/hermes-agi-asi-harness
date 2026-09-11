"""Tests for the ExperimentDesigner agent."""

import pytest
from deepresearch.agents.experiment_designer import ExperimentDesigner
from deepresearch.state import new_research_state, PipelineStage, AgentRole, Hypothesis


@pytest.fixture
def hypothesis():
    return Hypothesis(
        id="hyp_0_0001",
        statement="Replacing dense attention with sparse attention will reduce compute cost by 50% without quality loss.",
        rationale="Sparse attention has been shown to maintain quality with reduced computation.",
        counterfactual_basis="If dense attention were optimal, sparse variants would show no benefit.",
        novelty_score=0.85,
        supporting_papers=["p1", "p2"],
        falsifiability=True,
        estimated_resource_cost="moderate",
    )


class TestExperimentDesigner:
    def test_init(self):
        designer = ExperimentDesigner()
        assert designer.config is not None

    def test_design(self, hypothesis):
        designer = ExperimentDesigner()
        exp = designer.design(hypothesis, [])
        assert exp["experiment_type"] in ("simulation", "computational", "analytical")
        assert exp["description"] != ""
        assert exp["methodology"] != ""
        assert isinstance(exp["required_resources"], list)
        assert exp["estimated_timeline"] != ""
        assert exp["simulated_outcome"] != ""
        assert isinstance(exp["confidence_intervals"], dict)

    def test_run(self):
        designer = ExperimentDesigner()
        state = new_research_state(query="test")
        state["hypotheses"] = [
            Hypothesis(
                id="hyp_0",
                statement="Test hypothesis",
                rationale="Testing",
                counterfactual_basis="If-then",
                novelty_score=0.8,
                supporting_papers=[],
                falsifiability=True,
                estimated_resource_cost="low",
            )
        ]
        state = designer.run(state)
        assert state["stage"] == PipelineStage.VALIDATE
        assert state["current_agent"] == AgentRole.EXPERIMENT
        assert len(state["experiments"]) == 1

    def test_run_no_hypotheses(self):
        designer = ExperimentDesigner()
        state = new_research_state(query="test")
        state = designer.run(state)
        assert len(state["experiments"]) == 0
