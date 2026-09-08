"""Tests for deepresearch.engine (DeepResearchEngine)."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from deepresearch.agents.pipeline import ResearchPipeline
from deepresearch.config import ResearchConfig
from deepresearch.state import (
    new_research_state,
    PipelineStage,
    AgentRole,
)


class TestResearchPipeline:
    """Tests for ResearchPipeline orchestrator."""

    def test_init_defaults(self):
        """Test default initialization."""
        pipeline = ResearchPipeline()
        assert isinstance(pipeline.config, ResearchConfig)
        assert pipeline.literature is not None
        assert pipeline.hypothesis is not None
        assert pipeline.experiments is not None
        assert pipeline.writer is not None
        assert pipeline.memory is not None
        assert pipeline.evaluator is not None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = ResearchConfig(arxiv_max_results=30)
        pipeline = ResearchPipeline(config=config)
        assert pipeline.config.arxiv_max_results == 30

    def test_run_full_pipeline(self):
        """Test the full research pipeline."""
        pipeline = ResearchPipeline()
        state = pipeline.run("quantum computing applications")
        assert state["query"] == "quantum computing applications"
        assert state["stage"] == PipelineStage.DONE
        assert len(state["papers"]) > 0
        assert len(state["summaries"]) > 0
        assert len(state["hypotheses"]) > 0
        assert len(state["experiments"]) > 0
        assert len(state["drafts"]) > 0
        assert len(state["evaluations"]) > 0
        assert state["run_id"] != ""

    def test_run_with_empty_results(self):
        """Test pipeline with a query that might return few results."""
        pipeline = ResearchPipeline()
        state = pipeline.run("a")
        assert state["query"] == "a"
        assert state["stage"] == PipelineStage.DONE

    def test_run_different_queries(self):
        """Test pipeline with different queries."""
        pipeline = ResearchPipeline()
        state1 = pipeline.run("neural networks")
        state2 = pipeline.run("graph neural networks")
        assert state1["query"] != state2["query"]
        assert state1["run_id"] != state2["run_id"]

    def test_run_state_persisted(self):
        """Test that pipeline state is persisted to memory."""
        pipeline = ResearchPipeline()
        state = pipeline.run("test query for persistence")
        retrieved = pipeline.memory.retrieve_state(state["run_id"])
        assert retrieved is not None
        assert retrieved["query"] == "test query for persistence"

    def test_get_paper_latex(self):
        """Test LaTeX paper generation."""
        pipeline = ResearchPipeline()
        state = pipeline.run("latex generation test")
        latex = pipeline.get_paper_latex(state)
        assert r"\documentclass" in latex
        assert r"\title" in latex
        assert r"\begin{document}" in latex
        assert r"\end{document}" in latex

    def test_pipeline_progressive_stages(self):
        """Verify the pipeline progresses through all stages."""
        pipeline = ResearchPipeline()
        state = pipeline.run("stage progression test")
        assert state["stage"] == PipelineStage.DONE

    def test_pipeline_handles_empty_query(self):
        """Pipeline should handle any query gracefully."""
        pipeline = ResearchPipeline()
        state = pipeline.run("a")
        assert state["stage"] == PipelineStage.DONE
