#!/usr/bin/env python3
"""
HERMES DEEP RESEARCH ENGINE — MAIN PLUGIN
===========================================
Integrates all research components into a unified deep research system.

This is the main entry point for the Deep Research Engine.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from core.runtime.plugin_base import PluginBase, PluginManifest

logger = logging.getLogger("hermes_deep_research")


class DeepResearchPlugin(PluginBase):
    """
    Deep Research Plugin — comprehensive autonomous research engine.
    
    Integrates:
    - Research Director (planning + decomposition)
    - Web Research Agent (search + crawl + extract)
    - Evidence Store (source ranking + contradiction detection)
    - Multi-Perspective Research (STORM-style)
    - DAG Research Executor (DeepResearch Agent-style)
    - Critic Engine (verification + citation checking)
    - Report Generator (citation-backed reports)
    """
    
    def __init__(self):
        self.manifest = None
        self._director = None
        self._web_agent = None
        self._evidence_store = None
        self._perspective_research = None
        self._dag_executor = None
        self._critic = None
        self._report_generator = None
    
    async def load(self) -> bool:
        """Load the plugin."""
        from .director import ResearchDirector
        from .agents import WebResearchAgent
        from .evidence import EvidenceStore
        from .perspective import MultiPerspectiveResearch
        from .dag import DAGResearchExecutor
        from .critic import CriticEngine
        from .report import ReportGenerator
        
        self._director = ResearchDirector()
        self._web_agent = WebResearchAgent()
        self._evidence_store = EvidenceStore()
        self._perspective_research = MultiPerspectiveResearch()
        self._dag_executor = DAGResearchExecutor()
        self._critic = CriticEngine()
        self._report_generator = ReportGenerator()
        
        logger.info("Deep Research Engine loaded")
        return True
    
    async def start(self) -> bool:
        """Start the plugin."""
        logger.info("Deep Research Engine started")
        return True
    
    async def stop(self) -> bool:
        """Stop the plugin."""
        logger.info("Deep Research Engine stopped")
        return True
    
    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "director": self._director is not None,
            "web_agent": self._web_agent is not None,
            "evidence_store": self._evidence_store is not None,
            "perspective_research": self._perspective_research is not None,
            "dag_executor": self._dag_executor is not None,
            "critic": self._critic is not None,
            "report_generator": self._report_generator is not None
        }
    
    async def research(self, topic: str, depth: int = 3) -> Dict[str, Any]:
        """
        Conduct deep research on a topic.
        
        Args:
            topic: The research topic
            depth: Research depth (1-5)
            
        Returns:
            Research report with citations
        """
        logger.info("Starting deep research: %s (depth=%d)", topic, depth)
        
        # Step 1: Create research plan
        plan = await self._director.create_plan(topic)
        
        # Step 2: Discover perspectives
        perspectives = await self._perspective_research.discover_perspectives(topic)
        
        # Step 3: Search and crawl
        search_results = []
        for query in plan.search_queries[:5]:
            results = await self._web_agent.search(query, num_results=5)
            search_results.extend(results)
        
        # Step 4: Crawl top results and extract evidence
        evidence = []
        for result in search_results[:10]:
            page = await self._web_agent.crawl(result.url)
            if page:
                # Add to evidence store
                source_id = self._evidence_store.add_source(
                    url=result.url,
                    title=result.title,
                    content=page.content
                )
                
                # Extract evidence
                extracted = await self._web_agent.extract_evidence(page, topic)
                evidence.extend(extracted)
                
                # Add to evidence store
                for e in extracted:
                    self._evidence_store.add_evidence(
                        claim=e.claim,
                        source_id=source_id,
                        confidence=e.confidence
                    )
        
        # Step 5: Curate knowledge from perspectives
        knowledge = await self._perspective_research.curate_knowledge(topic)
        
        # Step 6: Build and execute DAG
        dag = self._dag_executor.build_dag(topic)
        dag_results = await self._dag_executor.execute()
        
        # Step 7: Critic review
        research_data = {
            "topic": topic,
            "evidence": [{"claim": e.claim, "source": e.url, "confidence": e.confidence} for e in evidence],
            "perspectives": [{"name": p.name, "description": p.description} for p in perspectives],
            "contradictions": self._evidence_store.get_contradictions()
        }
        
        quality_score = await self._critic.assess_quality(research_data)
        review = await self._critic.red_team_review(research_data)
        
        # Step 8: Generate report
        report = await self._report_generator.generate_report(
            topic=topic,
            evidence=[{"claim": e.claim, "source": e.url, "confidence": e.confidence} for e in evidence],
            perspectives=[{"name": p.name, "description": p.description} for p in perspectives],
            quality_score=quality_score.overall
        )
        
        # Render report
        rendered_report = self._report_generator.render_report(report)
        
        logger.info("Deep research complete: %s (%d findings)", topic[:50], len(evidence))
        
        return {
            "topic": topic,
            "plan_id": plan.plan_id,
            "perspectives": len(perspectives),
            "sources_searched": len(search_results),
            "evidence_found": len(evidence),
            "contradictions": len(self._evidence_store.get_contradictions()),
            "quality_score": quality_score.overall,
            "review": review,
            "report": rendered_report
        }


# Plugin entry point
class Plugin(DeepResearchPlugin):
    pass
