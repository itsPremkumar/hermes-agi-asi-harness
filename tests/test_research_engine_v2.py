"""Tests for the Research Engine v2 Plugin — evidence graph (v7 §18-19).

Covers: Source, EvidenceClaim, EvidenceGraph, ResearchEngineV2, ResearchEngineV2Plugin
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from plugins.research_engine_v2 import (
    EvidenceClaim,
    EvidenceGraph,
    ResearchEngineV2,
    ResearchEngineV2Plugin,
    Source,
)
from plugins.research_engine_v2 import (
    create as create_research_engine,
)


class TestSource:
    """Tests for Source dataclass."""

    def test_create_source(self):
        s = Source(id="s1", url="https://example.com", title="Example", authority="high")
        assert s.id == "s1"
        assert s.authority == "high"
        # trust_level defaults to 0.5 in dataclass; computed in add_source
        assert s.trust_level == 0.5

    def test_create_with_defaults(self):
        s = Source(id="s2", url="https://example.com", title="Test")
        assert s.authority == "none"
        assert s.trust_level == 0.5


class TestEvidenceClaim:
    """Tests for EvidenceClaim dataclass."""

    def test_create_claim(self):
        c = EvidenceClaim(id="c1", proposition="AI is useful", confidence=0.8)
        assert c.id == "c1"
        assert c.proposition == "AI is useful"
        assert c.confidence == 0.8
        assert c.status == "unverified"


class TestEvidenceGraph:
    """Tests for the EvidenceGraph."""

    def test_add_source(self):
        graph = EvidenceGraph()
        s = graph.add_source("https://arxiv.org/123", "Paper", authority="high", content="abstract")
        assert s.id is not None
        assert s.authority == "high"
        # trust_level is computed in add_source
        assert s.trust_level == 0.9
        assert len(graph._sources) == 1

    def test_add_claim(self):
        graph = EvidenceGraph()
        c = graph.add_claim("AI agents are improving", confidence=0.7)
        assert c.id is not None
        assert c.proposition == "AI agents are improving"
        assert len(graph._claims) == 1

    def test_support_claim(self):
        graph = EvidenceGraph()
        s = graph.add_source("https://example.com", "Source", authority="high")
        c = graph.add_claim("Claim", confidence=0.5)
        graph.support_claim(c.id, s.id)
        assert s.id in c.supported_by
        assert c.confidence > 0.5

    def test_contradict_claim(self):
        graph = EvidenceGraph()
        s = graph.add_source("https://example.com", "Source", authority="high")
        c = graph.add_claim("Claim", confidence=0.5)
        graph.contradict_claim(c.id, s.id)
        assert s.id in c.contradicted_by
        assert c.confidence < 0.5

    def test_contradiction_changes_status(self):
        graph = EvidenceGraph()
        s1 = graph.add_source("https://example.com", "S1", authority="high")
        s2 = graph.add_source("https://example.com", "S2", authority="high")
        c = graph.add_claim("Claim", confidence=0.5)
        graph.contradict_claim(c.id, s1.id)
        graph.contradict_claim(c.id, s2.id)
        assert c.status == "contradicted"

    def test_find_contradictions(self):
        graph = EvidenceGraph()
        s1 = graph.add_source("https://example.com", "S1", authority="medium")
        s2 = graph.add_source("https://example.com", "S2", authority="medium")
        c = graph.add_claim("Claim", confidence=0.5)
        graph.support_claim(c.id, s1.id)
        graph.contradict_claim(c.id, s2.id)
        contradictions = graph.find_contradictions()
        assert len(contradictions) == 1
        assert contradictions[0]["supporting"] == 1
        assert contradictions[0]["contradicting"] == 1

    def test_get_claims_for_source(self):
        graph = EvidenceGraph()
        s = graph.add_source("https://example.com", "Source", authority="high")
        c1 = graph.add_claim("Claim 1")
        c2 = graph.add_claim("Claim 2")
        graph.support_claim(c1.id, s.id)
        graph.contradict_claim(c2.id, s.id)
        claims = graph.get_claims_for_source(s.id)
        assert len(claims) == 2

    def test_get_stats(self):
        graph = EvidenceGraph()
        graph.add_source("https://example.com", "S", authority="high")
        graph.add_claim("C1")
        graph.add_claim("C2")
        stats = graph.get_stats()
        assert stats["claims"] == 2
        assert stats["sources"] == 1


class TestResearchEngineV2:
    """Tests for the ResearchEngineV2."""

    def test_create(self):
        engine = ResearchEngineV2()
        assert engine.graph is not None
        assert len(engine._reports) == 0

    def test_research_with_sources(self):
        engine = ResearchEngineV2()
        report = engine.research("What is AI agents?", sources=[
            {"url": "https://example.com", "title": "AI Agents", "authority": "high"},
        ])
        assert report.id is not None
        assert report.question == "What is AI agents?"
        assert "P1_discovery" in report.passes_completed
        assert len(report.sources) == 1

    def test_research_without_sources(self):
        engine = ResearchEngineV2()
        report = engine.research("Test question")
        assert report.question == "Test question"
        assert len(report.sources) == 0

    def test_research_stores_report(self):
        engine = ResearchEngineV2()
        engine.research("Q1")
        engine.research("Q2")
        assert len(engine._reports) == 2

    def test_get_stats(self):
        engine = ResearchEngineV2()
        engine.research("Test")
        stats = engine.get_stats()
        assert stats["reports"] == 1
        assert "claims" in stats
        assert "sources" in stats

    def test_report_has_all_passes(self):
        engine = ResearchEngineV2()
        report = engine.research("Test")
        assert "P1_discovery" in report.passes_completed
        assert "P2_primary" in report.passes_completed
        assert "P3_cross_validation" in report.passes_completed
        assert "P4_contradiction" in report.passes_completed
        assert "P5_synthesis" in report.passes_completed
        assert "P6_verification" in report.passes_completed


class TestResearchEngineV2Plugin:
    """Tests for the ResearchEngineV2Plugin wrapper."""

    @pytest.mark.asyncio
    async def test_create(self):
        plugin = ResearchEngineV2Plugin()
        assert plugin.engine is not None

    @pytest.mark.asyncio
    async def test_create_with_kernel(self):
        plugin = await create_research_engine(kernel="fake_kernel")
        assert plugin._kernel == "fake_kernel"

    @pytest.mark.asyncio
    async def test_load(self):
        plugin = ResearchEngineV2Plugin()
        await plugin.load()

    @pytest.mark.asyncio
    async def test_start_stop(self):
        plugin = ResearchEngineV2Plugin()
        await plugin.start()
        await plugin.stop()

    @pytest.mark.asyncio
    async def test_health(self):
        plugin = ResearchEngineV2Plugin()
        h = await plugin.health()
        assert h["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_research(self):
        plugin = ResearchEngineV2Plugin()
        report = await plugin.research("Test question")
        assert report.id is not None

    @pytest.mark.asyncio
    async def test_add_claim(self):
        plugin = ResearchEngineV2Plugin()
        claim = await plugin.add_claim("Test claim", confidence=0.8)
        assert claim.proposition == "Test claim"

    @pytest.mark.asyncio
    async def test_find_contradictions(self):
        plugin = ResearchEngineV2Plugin()
        contradictions = await plugin.find_contradictions()
        assert isinstance(contradictions, list)

    @pytest.mark.asyncio
    async def test_get_stats(self):
        plugin = ResearchEngineV2Plugin()
        stats = plugin.engine.get_stats()
        assert "reports" in stats


class TestResearchEngineIntegration:
    """Integration tests for research engine."""

    def test_full_evidence_lifecycle(self):
        engine = ResearchEngineV2()
        
        report = engine.research("AI safety importance", sources=[
            {"url": "https://arxiv.org/1", "title": "Safety Paper", "authority": "high", "content": "..."},
            {"url": "https://blog.com/1", "title": "Opinion", "authority": "low", "content": "..."},
        ])
        
        c1 = engine.graph.add_claim("AI safety is critical", confidence=0.8)
        engine.graph.add_claim("Some disagree", confidence=0.4)
        
        for s in report.sources:
            engine.graph.support_claim(c1.id, s.id)
        
        contradictions = engine.graph.find_contradictions()
        assert isinstance(contradictions, list)

    def test_confidence_updates_with_evidence(self):
        graph = EvidenceGraph()
        s = graph.add_source("https://example.com", "Source", authority="high")
        c = graph.add_claim("Claim", confidence=0.5)
        
        initial_conf = c.confidence
        graph.support_claim(c.id, s.id)
        assert c.confidence > initial_conf

    def test_source_trust_levels(self):
        graph = EvidenceGraph()
        low = graph.add_source("https://low.com", "Low", authority="low")
        high = graph.add_source("https://high.com", "High", authority="high")
        
        assert low.trust_level == 0.3
        assert high.trust_level == 0.9

    def test_claim_status_transitions(self):
        graph = EvidenceGraph()
        s1 = graph.add_source("https://s1.com", "S1", authority="high")
        s2 = graph.add_source("https://s2.com", "S2", authority="high")
        c = graph.add_claim("Claim", confidence=0.5)
        
        assert c.status == "unverified"
        graph.contradict_claim(c.id, s1.id)
        graph.contradict_claim(c.id, s2.id)
        assert c.status == "contradicted"

    def test_get_claims_for_source_integration(self):
        graph = EvidenceGraph()
        s = graph.add_source("https://example.com", "Source", authority="high")
        c1 = graph.add_claim("Supported claim")
        c2 = graph.add_claim("Contradicted claim")
        graph.add_claim("Unrelated claim")
        
        graph.support_claim(c1.id, s.id)
        graph.contradict_claim(c2.id, s.id)
        
        claims = graph.get_claims_for_source(s.id)
        assert len(claims) == 2
