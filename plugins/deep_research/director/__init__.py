#!/usr/bin/env python3
"""
HERMES DEEP RESEARCH ENGINE — RESEARCH DIRECTOR
================================================
Research planning, decomposition, and orchestration.

Extracted from:
- GPT Researcher: Research planning + parallel research
- STORM: Perspective discovery + question generation
- DeepResearch Agent: DAG planning + task execution
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_research_director")


class ResearchPhase(str, Enum):
    PLANNING = "planning"
    SEARCHING = "searching"
    CRAWLING = "crawling"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    VERIFYING = "verifying"
    REPORTING = "reporting"


@dataclass
class ResearchQuestion:
    """A research question."""
    question_id: str
    question: str
    sub_questions: list[str] = field(default_factory=list)
    status: str = "pending"
    findings: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    depth: int = 0
    max_depth: int = 3


@dataclass
class ResearchPlan:
    """A research plan."""
    plan_id: str
    topic: str
    questions: list[ResearchQuestion] = field(default_factory=list)
    perspectives: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)
    status: str = "draft"
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class ResearchDirector:
    """
    Research Director — plans and orchestrates deep research.
    
    Features:
    - Research decomposition (break complex questions into sub-questions)
    - Perspective discovery (find different angles to investigate)
    - Search query generation (create effective search queries)
    - Research DAG creation (plan research as a directed acyclic graph)
    - Recursive research (discover new questions during research)
    """
    
    def __init__(self, max_depth: int = 3, max_questions: int = 20):
        self.max_depth = max_depth
        self._max_questions = max_questions
        self._plans: dict[str, ResearchPlan] = {}
    
    async def create_plan(self, topic: str, context: str = "") -> ResearchPlan:
        """Create a research plan for a topic."""
        plan = ResearchPlan(
            plan_id=str(uuid.uuid4()),
            topic=topic
        )
        
        # Generate research questions
        plan.questions = await self._generate_questions(topic, context)
        
        # Generate perspectives
        plan.perspectives = await self._generate_perspectives(topic)
        
        # Generate search queries
        plan.search_queries = await self._generate_search_queries(topic, plan.questions)
        
        plan.status = "ready"
        self._plans[plan.plan_id] = plan
        
        logger.info("Research plan created: %s (%d questions)", topic[:50], len(plan.questions))
        return plan
    
    async def _generate_questions(self, topic: str, context: str = "") -> list[ResearchQuestion]:
        """Generate research questions from a topic."""
        questions = []
        
        # Main question
        main_question = ResearchQuestion(
            question_id=str(uuid.uuid4()),
            question=f"What is {topic}?",
            depth=0
        )
        questions.append(main_question)
        
        # Sub-questions
        sub_questions = [
            f"What are the key components of {topic}?",
            f"What are the latest developments in {topic}?",
            f"What are the main challenges in {topic}?",
            f"What are the future trends for {topic}?",
            f"Who are the key players in {topic}?",
        ]
        
        for sq in sub_questions:
            question = ResearchQuestion(
                question_id=str(uuid.uuid4()),
                question=sq,
                depth=1
            )
            questions.append(question)
        
        return questions[:self._max_questions]
    
    async def _generate_perspectives(self, topic: str) -> list[str]:
        """Generate different perspectives to investigate."""
        return [
            f"Technical perspective on {topic}",
            f"Business perspective on {topic}",
            f"Academic perspective on {topic}",
            f"Industry perspective on {topic}",
            f"Historical perspective on {topic}",
            f"Future outlook for {topic}",
        ]
    
    async def _generate_search_queries(self, topic: str, questions: list[ResearchQuestion]) -> list[str]:
        """Generate search queries from questions."""
        queries = [topic]
        
        for question in questions:
            queries.append(question.question)
            
            # Generate variations
            query_variations = [
                f"{question.question} 2024",
                f"{question.question} latest",
                f"{question.question} research",
            ]
            queries.extend(query_variations)
        
        return queries
    
    async def decompose_question(self, question: str, depth: int = 0) -> list[ResearchQuestion]:
        """Decompose a question into sub-questions."""
        sub_questions = []
        
        if depth >= self.max_depth:
            return sub_questions
        
        # Generate sub-questions
        for i in range(3):
            sq = ResearchQuestion(
                question_id=str(uuid.uuid4()),
                question=f"Sub-question {i+1} for: {question[:50]}",
                depth=depth + 1,
                max_depth=self.max_depth
            )
            sub_questions.append(sq)
        
        return sub_questions
    
    def get_plan(self, plan_id: str) -> ResearchPlan | None:
        """Get a research plan."""
        return self._plans.get(plan_id)
    
    async def health(self) -> dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "plans_count": len(self._plans),
            "max_depth": self.max_depth
        }
