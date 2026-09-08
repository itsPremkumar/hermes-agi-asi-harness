"""
Research Pipeline

Orchestrates the multi-agent pipeline: Search -> Read -> Synthesize ->
Hypothesize -> Validate -> Write. This is the top-level state machine
that chains agents together.
"""

from __future__ import annotations

import json
import uuid

from deepresearch.agents.literature_reviewer import LiteratureReviewer
from deepresearch.agents.hypothesis_generator import HypothesisGenerator
from deepresearch.agents.experiment_designer import ExperimentDesigner
from deepresearch.agents.paper_writer import PaperWriter
from deepresearch.config import ResearchConfig
from deepresearch.state import (
    PipelineStage,
    ResearchState,
    new_research_state,
)
from deepresearch.memory.research_memory import ResearchMemory
from deepresearch.evaluation.quality_evaluator import QualityEvaluator


class ResearchPipeline:
    """Multi-agent research pipeline orchestrator."""

    def __init__(self, config: ResearchConfig | None = None):
        self.config = config or ResearchConfig()
        self.literature = LiteratureReviewer(self.config)
        self.hypothesis = HypothesisGenerator(self.config)
        self.experiments = ExperimentDesigner(self.config)
        self.writer = PaperWriter(self.config)
        self.memory = ResearchMemory(self.config)
        self.evaluator = QualityEvaluator(self.config)
        self.state: ResearchState | None = None

    def run(self, query: str) -> ResearchState:
        """Run the full research pipeline for a given query."""
        run_id = str(uuid.uuid4())
        state = new_research_state(query=query, run_id=run_id)
        self.state = state

        # Stage 1: Search + Read (Literature Reviewer)
        state = self.literature.run(state)
        self.memory.store_state(state)

        # Stage 2: Synthesize + Hypothesize
        state = self.hypothesis.run(state)
        self.memory.store_state(state)

        # Stage 3: Validate (Experiment Designer)
        state = self.experiments.run(state)
        self.memory.store_state(state)

        # Stage 4: Write
        state = self.writer.run(state)
        self.memory.store_state(state)

        # Stage 5: Evaluate
        eval_result = self.evaluator.evaluate(state)
        state["evaluations"] = [eval_result]
        state["stage"] = PipelineStage.DONE
        self.memory.store_state(state)

        return state

    def get_paper_latex(self, state: ResearchState) -> str:
        """Generate full LaTeX from a completed pipeline run."""
        if not state.get("drafts"):
            return ""

        draft = state["drafts"][-1]
        latex_parts = [
            "\\documentclass{article}\n",
            "\\usepackage{geometry}\n",
            "\\usepackage{hyperref}\n",
            "\\geometry{a4paper, margin=1in}\n",
            f"\\title{{{draft['title']}}}\n",
            "\\author{DeepResearch Engine}\n",
            "\\date{\\today}\n",
            "\\begin{document}\n",
            "\\maketitle\n",
            f"\\begin{{abstract}}\n{draft['abstract']}\n\\end{{abstract}}\n",
        ]

        for section_name, content in draft.get("sections", {}).items():
            if section_name == "Introduction":
                latex_parts.append(f"\\section{{{section_name}}}\n{content}\n")
            else:
                latex_parts.append(f"\\section{{{section_name}}}\n{content}\n")

        latex_parts.extend([
            "\\bibliographystyle{plain}\n",
            "\\bibliography{references}\n",
            "\\end{document}\n",
        ])

        # Write bibliography file
        bib_content = draft.get("bibliography_tex", "")
        if bib_content:
            import os
            os.makedirs("build", exist_ok=True)
            bib_path = "build/references.bib"
            with open(bib_path, "w") as f:
                f.write(bib_content)

        return "\n".join(latex_parts)

    def run_from_config_file(self, config_path: str) -> ResearchState:
        """Run the pipeline with a JSON config file."""
        with open(config_path) as f:
            config_data = json.load(f)
        query = config_data.get("query", "")
        return self.run(query)
