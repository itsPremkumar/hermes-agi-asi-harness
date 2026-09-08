"""
Core DeepResearch Engine.

Orchestrates the multi-agent pipeline:
Search -> Read -> Synthesize -> Hypothesize -> Validate -> Write
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from deepresearch.agents import (
    ExperimentDesignerAgent,
    HypothesisGeneratorAgent,
    LiteratureReviewerAgent,
    PaperWriterAgent,
)
from deepresearch.config import DeepResearchConfig
from deepresearch.memory import ResearchMemory
from deepresearch.models import (
    ExperimentDesign,
    Hypothesis,
    Paper,
    PaperStatus,
    ResearchPlan,
    ResearchStage,
    SynthesisResult,
)
from deepresearch.tools import ArxivTool, CitationGraphTool, PubMedTool

logger = logging.getLogger(__name__)


class DeepResearchEngine:
    """Main research engine that orchestrates the agent pipeline."""

    def __init__(
        self,
        config: Optional[DeepResearchConfig] = None,
        tools: Optional[dict[str, Any]] = None,
        agents: Optional[dict[str, Any]] = None,
    ):
        """Initialize the engine.

        Args:
            config: Configuration object. If None, loads defaults.
            tools: Optional dict of tools to use. Defaults to standard toolset.
            agents: Optional dict of agents. Defaults to standard agents.
        """
        self.config = config or DeepResearchConfig()
        self.tools = tools or self._default_tools()
        self.agents = agents or self._default_agents()
        self.memory = ResearchMemory(self.config.memory_dir)

        # Track active research plans
        self._plans: dict[str, ResearchPlan] = {}

    def _default_tools(self) -> dict[str, Any]:
        """Create the default toolset."""
        return {
            "arxiv": ArxivTool(self.config),
            "pubmed": PubMedTool(self.config),
            "citation": CitationGraphTool(),
        }

    def _default_agents(self) -> dict[str, Any]:
        """Create the default agent set."""
        return {
            "literature_reviewer": LiteratureReviewerAgent(self.config, self.tools, self.memory),
            "hypothesis_generator": HypothesisGeneratorAgent(self.config, self.tools),
            "experiment_designer": ExperimentDesignerAgent(self.config, self.tools),
            "paper_writer": PaperWriterAgent(self.config, self.tools),
        }

    async def research(self, query: str, max_papers: int = 50) -> ResearchPlan:
        """Run the full research pipeline on a query.

        Args:
            query: Research query/topic.
            max_papers: Maximum number of papers to fetch.

        Returns:
            Completed ResearchPlan with papers, hypotheses, experiments, and final paper.
        """
        plan = ResearchPlan(query=query)
        plan_id = str(uuid.uuid4())
        self._plans[plan_id] = plan

        logger.info("Starting research on: %s", query)

        # Stage 1: Search
        logger.info("Stage: Search")
        plan.stage = ResearchStage.SEARCH
        papers = await self._search(query, max_papers)
        plan.papers = papers
        self.memory.save_papers(papers)

        # Stage 2: Read (fetch full content)
        logger.info("Stage: Read")
        plan.stage = ResearchStage.READ
        papers = await self._read_papers(papers)
        plan.papers = papers

        # Stage 3: Synthesize
        logger.info("Stage: Synthesize")
        plan.stage = ResearchStage.SYNTHESIZE
        synthesis = await self.agents["literature_reviewer"].synthesize(papers)
        plan.synthesis = synthesis

        # Stage 4: Hypothesize
        logger.info("Stage: Hypothesize")
        plan.stage = ResearchStage.HYPOTHESIZE
        hypotheses = await self.agents["hypothesis_generator"].generate(
            synthesis, papers
        )
        plan.hypotheses = hypotheses
        self.memory.save_hypotheses(hypotheses)

        # Stage 5: Validate (Design Experiments)
        logger.info("Stage: Validate")
        plan.stage = ResearchStage.VALIDATE
        experiments = await self._validate_hypotheses(hypotheses)
        plan.experiments = experiments
        self.memory.save_experiments(experiments)

        # Stage 6: Write
        logger.info("Stage: Write")
        plan.stage = ResearchStage.WRITE
        paper = await self.agents["paper_writer"].write(plan)
        plan.final_paper = paper
        plan.stage = ResearchStage.COMPLETE

        self.memory.save_plan(plan)
        logger.info("Research complete. Plan ID: %s", plan_id)

        return plan

    async def _search(self, query: str, max_papers: int) -> list[Paper]:
        """Search multiple sources for papers."""
        arxiv_results = await self.tools["arxiv"].search(query, max_papers // 2)
        pubmed_results = await self.tools["pubmed"].search(query, max_papers // 2)
        return arxiv_results + pubmed_results

    async def _read_papers(self, papers: list[Paper]) -> list[Paper]:
        """Fetch full content for papers."""
        tasks = [self._read_paper_async(p) for p in papers]
        return await asyncio.gather(*tasks)

    async def _read_paper_async(self, paper: Paper) -> Paper:
        """Read a single paper's full content."""
        try:
            if paper.source.value == "arxiv":
                content = await self.tools["arxiv"].fetch_full_text(paper.id)
            elif paper.source.value == "pubmed":
                content = await self.tools["pubmed"].fetch_full_text(paper.id)
            else:
                content = paper.abstract

            if content:
                paper.content = content
                paper.status = PaperStatus.ANALYZED if paper.content else PaperStatus.FETCHED
            return paper
        except Exception as e:
            logger.warning("Failed to read paper %s: %s", paper.id, e)
            return paper

    async def _validate_hypotheses(
        self, hypotheses: list[Hypothesis]
    ) -> list[ExperimentDesign]:
        """Design experiments to validate hypotheses."""
        experiments = []
        for hyp in hypotheses:
            exp = await self.agents["experiment_designer"].design(hyp)
            experiments.append(exp)
        return experiments

    def get_plan(self, plan_id: str) -> Optional[ResearchPlan]:
        """Retrieve a research plan by ID."""
        return self._plans.get(plan_id)

    def clear(self) -> None:
        """Clear all in-memory plans."""
        self._plans.clear()


__all__ = ["DeepResearchEngine"]
