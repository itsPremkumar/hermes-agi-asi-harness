#!/usr/bin/env python3
"""
HERMES DEEP RESEARCH ENGINE — EVIDENCE STORE
==============================================
Source ranking, contradiction detection, and evidence management.

Extracted from:
- GPT Researcher: Evidence collection + source ranking
- DeepResearch Agent: Shared memory + cross-verification
- STORM: Knowledge collection + contradiction detection
"""

from __future__ import annotations

import hashlib
import re
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_evidence_store")


class SourceCredibility(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    RAW = "raw"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    DEPRECATED = "deprecated"


@dataclass
class Source:
    """A source of information."""
    source_id: str
    url: str
    title: str
    content: str
    credibility: SourceCredibility = SourceCredibility.UNKNOWN
    relevance_score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Evidence:
    """A piece of evidence."""
    evidence_id: str
    claim: str
    source: Source
    status: EvidenceStatus = EvidenceStatus.RAW
    confidence: float = 0.5
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Contradiction:
    """A contradiction between evidence."""
    contradiction_id: str
    evidence_a_id: str
    evidence_b_id: str
    description: str
    severity: float = 0.5
    resolved: bool = False
    resolution: str = ""
    timestamp: float = field(default_factory=time.time)


class EvidenceStore:
    """
    Evidence Store — manages sources, evidence, and contradictions.
    
    Features:
    - Source credibility assessment
    - Evidence ranking and filtering
    - Contradiction detection
    - Cross-verification
    - Evidence deduplication
    """
    
    def __init__(self):
        self._sources: dict[str, Source] = {}
        self._evidence: dict[str, Evidence] = {}
        self._contradictions: list[Contradiction] = []
    
    def add_source(self, url: str, title: str, content: str,
                   credibility: SourceCredibility = SourceCredibility.UNKNOWN) -> str:
        """Add a source."""
        source_id = str(uuid.uuid4())
        
        source = Source(
            source_id=source_id,
            url=url,
            title=title,
            content=content,
            credibility=credibility
        )
        
        self._sources[source_id] = source
        return source_id
    
    def add_evidence(self, claim: str, source_id: str, confidence: float = 0.5) -> str:
        """Add evidence."""
        source = self._sources.get(source_id)
        if not source:
            return ""
        
        evidence_id = str(uuid.uuid4())
        
        evidence = Evidence(
            evidence_id=evidence_id,
            claim=claim,
            source=source,
            confidence=confidence
        )
        
        self._evidence[evidence_id] = evidence
        
        # Check for contradictions
        self._check_contradictions(evidence)
        
        return evidence_id
    
    def _check_contradictions(self, new_evidence: Evidence):
        """Check for contradictions with existing evidence."""
        for evidence_id, existing in self._evidence.items():
            if evidence_id == new_evidence.evidence_id:
                continue
            
            # Simple contradiction detection
            if self._is_contradiction(new_evidence.claim, existing.claim):
                contradiction = Contradiction(
                    contradiction_id=str(uuid.uuid4()),
                    evidence_a_id=new_evidence.evidence_id,
                    evidence_b_id=evidence_id,
                    description=f"Contradiction between: {new_evidence.claim[:50]} vs {existing.claim[:50]}",
                    severity=0.7
                )
                self._contradictions.append(contradiction)
                
                # Update evidence status
                new_evidence.contradicting_evidence.append(evidence_id)
                existing.contradicting_evidence.append(new_evidence.evidence_id)
    
    def _is_contradiction(self, claim_a: str, claim_b: str) -> bool:
        """Check if two claims contradict each other."""
        # Simple heuristic: check for negation patterns
        negation_patterns = [
            (r"\bnot\b", r"\b"),
            (r"\bnever\b", r"\balways\b"),
            (r"\bno\b", r"\byes\b"),
            (r"\bfalse\b", r"\btrue\b"),
        ]
        
        for pattern_a, pattern_b in negation_patterns:
            if re.search(pattern_a, claim_a, re.IGNORECASE) and re.search(pattern_b, claim_b, re.IGNORECASE):
                return True
        
        return False
    
    def rank_sources(self) -> list[Source]:
        """Rank sources by credibility and relevance."""
        sources = list(self._sources.values())
        
        # Score each source
        for source in sources:
            score = 0.0
            
            # Credibility score
            if source.credibility == SourceCredibility.HIGH:
                score += 0.4
            elif source.credibility == SourceCredibility.MEDIUM:
                score += 0.2
            
            # Relevance score
            score += source.relevance_score * 0.4
            
            # Recency score
            age_hours = (time.time() - source.timestamp) / 3600
            if age_hours < 24:
                score += 0.2
            elif age_hours < 168:  # 1 week
                score += 0.1
            
            source.metadata["rank_score"] = score
        
        sources.sort(key=lambda s: s.metadata.get("rank_score", 0), reverse=True)
        return sources
    
    def get_evidence_for_claim(self, claim: str) -> list[Evidence]:
        """Get evidence supporting a claim."""
        evidence_list = []
        
        for evidence in self._evidence.values():
            if claim.lower() in evidence.claim.lower():
                evidence_list.append(evidence)
        
        # Sort by confidence
        evidence_list.sort(key=lambda e: e.confidence, reverse=True)
        return evidence_list
    
    def get_contradictions(self) -> list[Contradiction]:
        """Get all contradictions."""
        return self._contradictions
    
    def resolve_contradiction(self, contradiction_id: str, resolution: str):
        """Resolve a contradiction."""
        for contradiction in self._contradictions:
            if contradiction.contradiction_id == contradiction_id:
                contradiction.resolved = True
                contradiction.resolution = resolution
                
                # Update evidence status
                evidence_a = self._evidence.get(contradiction.evidence_a_id)
                evidence_b = self._evidence.get(contradiction.evidence_b_id)
                
                if evidence_a and evidence_b:
                    # Keep the one with higher confidence
                    if evidence_a.confidence >= evidence_b.confidence:
                        evidence_b.status = EvidenceStatus.CONTRADICTED
                    else:
                        evidence_a.status = EvidenceStatus.CONTRADICTED
                
                break
    
    def get_statistics(self) -> dict[str, Any]:
        """Get statistics."""
        return {
            "sources": len(self._sources),
            "evidence": len(self._evidence),
            "contradictions": len(self._contradictions),
            "unresolved_contradictions": sum(1 for c in self._contradictions if not c.resolved),
            "verified_evidence": sum(1 for e in self._evidence.values() if e.status == EvidenceStatus.VERIFIED),
            "contradicted_evidence": sum(1 for e in self._evidence.values() if e.status == EvidenceStatus.CONTRADICTED),
        }
    
    async def health(self) -> dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            **self.get_statistics()
        }
