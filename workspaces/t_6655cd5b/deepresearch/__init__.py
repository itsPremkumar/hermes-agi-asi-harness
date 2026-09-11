"""
DeepResearch Engine — Autonomous Scientific Research Agent.

A multi-agent pipeline that reads academic papers, synthesizes findings,
identifies gaps, and generates novel research hypotheses.

Pipeline: Search → Read → Synthesize → Hypothesize → Validate → Write
"""

from deepresearch.state import (
    ResearchState,
    PaperSummary,
    Hypothesis,
    ExperimentDesign,
    PaperDraft,
    AgentRole,
    PipelineStage,
    EvaluationResult,
)
from deepresearch.config import ResearchConfig, DEFAULT_CONFIG

__version__ = "1.0.0"
__all__ = [
    "ResearchState",
    "PaperSummary",
    "Hypothesis",
    "ExperimentDesign",
    "PaperDraft",
    "AgentRole",
    "PipelineStage",
    "EvaluationResult",
    "ResearchConfig",
    "DEFAULT_CONFIG",
]
