#!/usr/bin/env python3
"""
HERMES UNCERTAINTY QUANTIFICATION PLANE
==========================================
Plugin for confidence calibration, unknown detection, and uncertainty reporting.

Extracted from:
- Research papers on calibrated classifiers (Guo et al. 2017)
- Evidential deep learning for uncertainty
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("hermes_uncertainty")


class ConfidenceLevel(str, Enum):
    HIGH = "high"      # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # 0.3 - 0.5
    VERY_LOW = "very_low"  # < 0.3


@dataclass
class UncertaintyReport:
    """Report on uncertainty for a claim or answer."""
    report_id: str
    claim: str
    confidence: float
    confidence_level: ConfidenceLevel
    known_unknowns: List[str]
    unknown_unknowns: List[str]
    calibration_factor: float
    recommendations: List[str]
    timestamp: float = field(default_factory=time.time)


class UncertaintyQuantifier:
    """
    Uncertainty Quantification Plane.
    
    Features:
    - Confidence calibration (correct overconfidence)
    - Known-unknown detection (gaps in knowledge)
    - Unknown-unknown detection (things we don't know we don't know)
    - "I don't know" triggering
    """
    
    def __init__(self):
        self._calibration_history: List[Dict[str, Any]] = []
        self._unknown_knowns: List[str] = []
    
    def calibrate_confidence(self, raw_confidence: float, source: str = "unknown") -> float:
        """Calibrate a confidence score."""
        # Get historical calibration for this source
        calibration_factor = self._get_calibration_factor(source)
        
        # Apply calibration
        calibrated = raw_confidence * calibration_factor
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, calibrated))
    
    def _get_calibration_factor(self, source: str) -> float:
        """Get calibration factor for a source based on history."""
        # Simple: if source has been overconfident in past, reduce
        source_history = [
            h for h in self._calibration_history
            if h.get("source") == source
        ]
        
        if not source_history:
            return 1.0
        
        # Calculate average error
        errors = []
        for h in source_history:
            predicted = h.get("predicted", 0.5)
            actual = h.get("actual", 0.5)
            errors.append(abs(predicted - actual))
        
        avg_error = sum(errors) / len(errors) if errors else 0.0
        
        # If overconfident (avg_error > 0.2), reduce confidence
        if avg_error > 0.2:
            return 0.8
        elif avg_error > 0.1:
            return 0.9
        else:
            return 1.0
    
    def detect_known_unknowns(self, question: str, evidence: List[Dict[str, Any]]) -> List[str]:
        """Detect known unknowns - things we know we don't know."""
        unknowns = []
        
        # Check for missing evidence
        if not evidence:
            unknowns.append("No evidence available")
        
        # Check for contradictory evidence
        contradictory = self._find_contradictions(evidence)
        if contradictory:
            unknowns.append(f"Contradictory evidence on: {', '.join(contradictory[:3])}")
        
        # Check for low confidence evidence
        low_confidence = [e for e in evidence if e.get("confidence", 0.5) < 0.3]
        if low_confidence:
            unknowns.append(f"Low confidence evidence on {len(low_confidence)} claims")
        
        # Check for missing sources
        missing_sources = self._identify_missing_sources(question, evidence)
        if missing_sources:
            unknowns.extend(missing_sources[:3])
        
        return unknowns
    
    def detect_unknown_unknowns(self, question: str, domain: str = "general") -> List[str]:
        """Detect unknown unknowns - things we don't know we don't know."""
        unknowns = []
        
        # Heuristic: complex questions in unfamiliar domains have unknown unknowns
        question_complexity = self._estimate_complexity(question)
        
        if question_complexity > 0.7:
            unknowns.append("High complexity question - may have unconsidered aspects")
        
        # Check for domain-specific unknowns
        if domain not in ["general", "common"]:
            unknowns.append(f"Unfamiliar domain ({domain}) - may miss domain-specific knowledge")
        
        # Check for temporal unknowns (rapidly changing fields)
        temporal_keywords = ["latest", "current", "recent", "new", "2024", "2025"]
        if any(kw in question.lower() for kw in temporal_keywords):
            unknowns.append("Temporal aspect - knowledge may be stale")
        
        return unknowns
    
    def _estimate_complexity(self, question: str) -> float:
        """Estimate question complexity (0-1)."""
        # Simple heuristic: length and keyword complexity
        words = question.split()
        complexity = min(1.0, len(words) / 50.0)
        
        complex_keywords = ["how", "why", "explain", "analyze", "compare", "evaluate"]
        for kw in complex_keywords:
            if kw in question.lower():
                complexity += 0.1
        
        return min(1.0, complexity)
    
    def _find_contradictions(self, evidence: List[Dict[str, Any]]) -> List[str]:
        """Find contradictions in evidence."""
        contradictions = []
        
        for i, e1 in enumerate(evidence):
            for e2 in evidence[i+1:]:
                if self._contradicts(e1, e2):
                    contradictions.append(f"{e1.get('claim', 'unknown')} vs {e2.get('claim', 'unknown')}")
        
        return contradictions
    
    def _contradicts(self, e1: Dict[str, Any], e2: Dict[str, Any]) -> bool:
        """Check if two evidence items contradict."""
        # Simple: different claims about same topic
        c1 = e1.get("claim", "").lower()
        c2 = e2.get("claim", "").lower()
        
        # Check for negation
        if c1.startswith("not ") and c2.startswith("not ") == False:
            if c1[4:] in c2 or c2 in c1[4:]:
                return True
        
        return False
    
    def _identify_missing_sources(self, question: str, evidence: List[Dict[str, Any]]) -> List[str]:
        """Identify missing sources."""
        missing = []
        existing_urls = {e.get("url", "") for e in evidence}
        
        # Check for academic sources
        has_academic = any("arxiv" in url or "scholar" in url for url in existing_urls)
        if not has_academic:
            missing.append("No academic sources")
        
        # Check for official sources
        has_official = any("gov" in url or "edu" in url for url in existing_urls)
        if not has_official:
            missing.append("No official sources")
        
        return missing
    
    def generate_report(self, claim: str, confidence: float, evidence: List[Dict[str, Any]], source: str = "unknown") -> UncertaintyReport:
        """Generate an uncertainty report."""
        calibrated = self.calibrate_confidence(confidence, source)
        
        # Determine confidence level
        if calibrated > 0.8:
            level = ConfidenceLevel.HIGH
        elif calibrated > 0.5:
            level = ConfidenceLevel.MEDIUM
        elif calibrated > 0.3:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.VERY_LOW
        
        known_unknowns = self.detect_known_unknowns(claim, evidence)
        unknown_unknowns = self.detect_unknown_unknowns(claim)
        
        recommendations = []
        if level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]:
            recommendations.append("Seek additional evidence")
            recommendations.append("Flag as unverified")
        if known_unknowns:
            recommendations.append("Address known unknowns")
        if unknown_unknowns:
            recommendations.append("Consider unknown unknowns")
        
        report = UncertaintyReport(
            report_id=str(uuid.uuid4()),
            claim=claim,
            confidence=calibrated,
            confidence_level=level,
            known_unknowns=known_unknowns,
            unknown_unknowns=unknown_unknowns,
            calibration_factor=self._get_calibration_factor(source),
            recommendations=recommendations
        )
        
        return report
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "calibration_history": len(self._calibration_history),
            "unknown_knowns": len(self._unknown_knowns),
        }
    
    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            **self.get_statistics()
        }


# Entry point
async def main():
    """Demo uncertainty quantifier."""
    uq = UncertaintyReport()
    
    # Test calibration
    print(f"Calibrated confidence: {uq.calibrate_confidence(0.9, 'test'):.2f}")
    
    # Test known unknowns
    unknowns = uq.detect_known_unknowns("What is AI?", [])
    print(f"Known unknowns: {unknowns}")
    
    # Test unknown unknowns
    unknowns = uq.detect_unknown_unknowns("How will AGI transform society by 2030?")
    print(f"Unknown unknowns: {unknowns}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
