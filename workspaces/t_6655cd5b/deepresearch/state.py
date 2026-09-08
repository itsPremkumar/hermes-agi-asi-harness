"""
TypedDict schemas for the DeepResearch engine.

These define the structured handoff payload between agents and the
internal state that flows through the pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import TypedDict, Optional


class AgentRole(str, Enum):
    LITERATURE = "literature_reviewer"
    HYPOTHESIS = "hypothesis_generator"
    EXPERIMENT = "experiment_designer"
    WRITER = "paper_writer"


class PipelineStage(str, Enum):
    SEARCH = "search"
    READ = "read"
    SYNTHESIZE = "synthesize"
    HYPOTHESIZE = "hypothesize"
    VALIDATE = "validate"
    WRITE = "write"
    DONE = "done"


class PaperMetadata(TypedDict, total=False):
    """Bibliographic metadata for a paper."""
    arxiv_id: str
    pubmed_id: str
    title: str
    authors: list[str]
    abstract: str
    year: int
    venue: str
    doi: str
    citations: int
    references: list[str]
    url: str


class PaperSummary(TypedDict):
    """Summary produced by the literature reviewer after reading a paper."""
    paper_id: str
    title: str
    authors: list[str]
    year: int
    abstract: str
    key_findings: list[str]
    methodology: str
    limitations: list[str]
    open_questions: list[str]
    citation_count: int
    url: str


class Hypothesis(TypedDict):
    """A generated research hypothesis with counterfactual reasoning."""
    id: str
    statement: str
    rationale: str
    counterfactual_basis: str
    novelty_score: float  # 0.0 - 1.0
    supporting_papers: list[str]
    falsifiability: bool
    estimated_resource_cost: str


class ExperimentDesign(TypedDict):
    """Automated experiment design for testing a hypothesis."""
    id: str
    hypothesis_id: str
    experiment_type: str  # "simulation" | "computational" | "analytical"
    description: str
    methodology: str
    required_resources: list[str]
    estimated_timeline: str
    simulated_outcome: str
    confidence_intervals: dict[str, float]


class PaperDraft(TypedDict):
    """A generated research paper draft in LaTeX format."""
    id: str
    title: str
    abstract: str
    sections: dict[str, str]  # section_name -> latex_content
    references: list[PaperMetadata]
    hypotheses: list[Hypothesis]
    experiment: Optional[ExperimentDesign]
    bibliography_tex: str


class EvaluationResult(TypedDict):
    """Result of the quality evaluator."""
    hypothesis_novelty: float
    experiment_feasibility: float
    paper_quality: float
    overall_score: float
    feedback: list[str]
    recommendations: list[str]


class ResearchState(TypedDict, total=False):
    """
    The central state object flowing through the research pipeline.

    This is the state machine state — each agent reads from it,
    produces output, and writes back to it before handing off.
    """
    # Pipeline control
    query: str
    stage: PipelineStage
    current_agent: AgentRole

    # Collected data
    papers: list[PaperMetadata]
    summaries: list[PaperSummary]
    hypotheses: list[Hypothesis]
    experiments: list[ExperimentDesign]
    drafts: list[PaperDraft]
    evaluations: list[EvaluationResult]

    # Citations / reference tracking
    citations_read: list[str]
    citation_graph: dict[str, list[str]]  # paper_id -> list of referenced paper_ids

    # Metadata
    run_id: str
    created_at: float
    updated_at: float
    error: Optional[str]


def new_research_state(query: str, run_id: str = "") -> ResearchState:
    """Create a fresh ResearchState for a new query."""
    import time
    import uuid

    if not run_id:
        run_id = str(uuid.uuid4())

    return ResearchState(
        query=query,
        stage=PipelineStage.SEARCH,
        current_agent=None,
        papers=[],
        summaries=[],
        hypotheses=[],
        experiments=[],
        drafts=[],
        evaluations=[],
        citations_read=[],
        citation_graph={},
        run_id=run_id,
        created_at=time.time(),
        updated_at=time.time(),
        error=None,
    )
