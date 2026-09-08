"""
Specialized agents for the DeepResearch pipeline.

Each agent is a stateless function that takes ResearchState + config
and returns updated state with its section populated.
"""

from deepresearch.agents.literature_reviewer import LiteratureReviewer
from deepresearch.agents.hypothesis_generator import HypothesisGenerator
from deepresearch.agents.experiment_designer import ExperimentDesigner
from deepresearch.agents.paper_writer import PaperWriter
from deepresearch.agents.pipeline import ResearchPipeline

__all__ = [
    "LiteratureReviewer",
    "HypothesisGenerator",
    "ExperimentDesigner",
    "PaperWriter",
    "ResearchPipeline",
]
