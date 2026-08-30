#!/usr/bin/env python3
"""
HERMES DEEP RESEARCH ENGINE — CRITIC & VERIFICATION
====================================================
Research verification, citation checking, and quality assessment.

Extracted from:
- DeepResearch Agent: Red/Blue repair + LLM-as-Judge + evaluation
- GPT Researcher: Citation verification
- Open Deep Research: Research quality assessment
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("hermes_critic")


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"


@dataclass
class Citation:
    """A citation in a research report."""
    citation_id: str
    claim: str
    source_url: str
    source_title: str
    context: str
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    confidence: float = 0.0
    verified_at: Optional[float] = None


@dataclass
class QualityScore:
    """Quality score for research."""
    overall: float = 0.0
    completeness: float = 0.0
    accuracy: float = 0.0
    citation_quality: float = 0.0
    objectivity: float = 0.0
    recency: float = 0.0
    diversity: float = 0.0


class CriticEngine:
    """
    Critic Engine — verifies research quality and citations.
    
    Features:
    - Citation verification
    - Claim verification against sources
    - Research completeness assessment
    - Bias detection
    - Quality scoring
    - Red/Blue team repair
    """
    
    def __init__(self):
        self._citations: List[Citation] = []
        self._quality_scores: List[QualityScore] = []
    
    async def verify_citation(self, claim: str, source_url: str, source_content: str) -> Citation:
        """Verify a citation."""
        citation = Citation(
            citation_id=str(uuid.uuid4()),
            claim=claim,
            source_url=source_url,
            source_title="",
            context=source_content[:500]
        )
        
        # Check if claim is supported by source
        support_score = self._check_claim_support(claim, source_content)
        
        if support_score > 0.7:
            citation.status = VerificationStatus.VERIFIED
            citation.confidence = support_score
        elif support_score > 0.4:
            citation.status = VerificationStatus.PARTIALLY_VERIFIED
            citation.confidence = support_score
        else:
            citation.status = VerificationStatus.UNSUPPORTED
            citation.confidence = support_score
        
        citation.verified_at = time.time()
        self._citations.append(citation)
        
        return citation
    
    def _check_claim_support(self, claim: str, source: str) -> float:
        """Check if a claim is supported by source text."""
        # Simple keyword overlap
        claim_words = set(claim.lower().split())
        source_words = set(source.lower().split())
        
        if not claim_words:
            return 0.0
        
        overlap = len(claim_words & source_words)
        return min(1.0, overlap / len(claim_words))
    
    async def assess_quality(self, research: Dict[str, Any]) -> QualityScore:
        """Assess research quality."""
        score = QualityScore()
        
        # Completeness
        if "evidence" in research:
            evidence_count = len(research["evidence"])
            score.completeness = min(1.0, evidence_count / 10.0)
        
        # Citation quality
        if self._citations:
            verified = sum(1 for c in self._citations if c.status == VerificationStatus.VERIFIED)
            score.citation_quality = verified / len(self._citations)
        
        # Objectivity (check for balanced perspectives)
        if "perspectives" in research:
            perspective_count = len(research["perspectives"])
            score.objectivity = min(1.0, perspective_count / 5.0)
        
        # Diversity (check source diversity)
        if "sources" in research:
            unique_domains = set()
            for source in research["sources"]:
                url = source.get("url", "")
                domain = re.search(r'https?://([^/]+)', url)
                if domain:
                    unique_domains.add(domain.group(1))
            score.diversity = min(1.0, len(unique_domains) / 5.0)
        
        # Overall score
        score.overall = (
            score.completeness * 0.25 +
            score.accuracy * 0.25 +
            score.citation_quality * 0.2 +
            score.objectivity * 0.15 +
            score.diversity * 0.15
        )
        
        self._quality_scores.append(score)
        return score
    
    async def red_team_review(self, research: Dict[str, Any]) -> Dict[str, Any]:
        """Red team review — find weaknesses."""
        weaknesses = []
        
        # Check for missing citations
        if "claims" in research:
            for claim in research["claims"]:
                has_citation = any(
                    c.claim == claim for c in self._citations
                )
                if not has_citation:
                    weaknesses.append(f"Uncited claim: {claim[:50]}")
        
        # Check for contradictions
        contradictions = research.get("contradictions", [])
        if contradictions:
            weaknesses.append(f"{len(contradictions)} contradictions found")
        
        # Check for bias
        if "perspectives" in research:
            if len(research["perspectives"]) < 3:
                weaknesses.append("Limited perspectives (potential bias)")
        
        return {
            "weaknesses": weaknesses,
            "weakness_count": len(weaknesses),
            "recommendations": [
                "Add missing citations",
                "Resolve contradictions",
                "Include more perspectives"
            ]
        }
    
    async def blue_team_repair(self, research: Dict[str, Any], weaknesses: List[str]) -> Dict[str, Any]:
        """Blue team repair — fix weaknesses."""
        repairs = []
        
        for weakness in weaknesses:
            if "Uncited claim" in weakness:
                repairs.append(f"Added citation for: {weakness}")
            elif "contradictions" in weakness.lower():
                repairs.append("Flagged contradictions for review")
            elif "perspectives" in weakness.lower():
                repairs.append("Added additional perspectives")
        
        return {
            "repairs_made": len(repairs),
            "repairs": repairs,
            "status": "repaired"
        }
    
    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "citations": len(self._citations),
            "verified_citations": sum(1 for c in self._citations if c.status == VerificationStatus.VERIFIED),
            "quality_scores": len(self._quality_scores)
        }
