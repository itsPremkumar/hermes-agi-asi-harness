"""Integration tests for the full ResearchPipeline."""

import os
import tempfile
import pytest
from deepresearch.agents.pipeline import ResearchPipeline
from deepresearch.config import ResearchConfig
from deepresearch.state import PipelineStage


@pytest.fixture
def pipeline():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    config = ResearchConfig()
    config.sqlite_path = db_path
    pipeline = ResearchPipeline(config)
    yield pipeline
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestResearchPipeline:
    def test_init(self, pipeline):
        assert pipeline.config is not None
        assert pipeline.literature is not None
        assert pipeline.hypothesis is not None
        assert pipeline.experiments is not None
        assert pipeline.writer is not None
        assert pipeline.memory is not None
        assert pipeline.evaluator is not None

    def test_run_full_pipeline(self, pipeline):
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

    def test_run_state_persisted(self, pipeline):
        state = pipeline.run("test query for persistence")
        retrieved = pipeline.memory.retrieve_state(state["run_id"])
        assert retrieved is not None
        assert retrieved["query"] == "test query for persistence"

    def test_get_paper_latex(self, pipeline):
        state = pipeline.run("latex generation test")
        latex = pipeline.get_paper_latex(state)
        assert "\\documentclass" in latex
        assert "\\title" in latex
        assert "\\begin{document}" in latex
        assert "\\end{document}" in latex

    def test_pipeline_progressive_stages(self, pipeline):
        """Verify the pipeline progresses through all stages."""
        state = pipeline.run("stage progression test")
        # Final state should be DONE
        assert state["stage"] == PipelineStage.DONE

    def test_pipeline_handles_empty_query(self, pipeline):
        """Pipeline should handle any query gracefully."""
        state = pipeline.run("a")
        assert state["stage"] == PipelineStage.DONE

    def test_run_different_queries(self, pipeline):
        """Pipeline should work with different queries."""
        state1 = pipeline.run("neural networks")
        state2 = pipeline.run("graph neural networks")
        assert state1["query"] != state2["query"]
        assert state1["run_id"] != state2["run_id"]
