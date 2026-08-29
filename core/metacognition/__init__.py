#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v6.0 — METACOGNITIVE MONITOR
====================================================
Self-monitoring, error detection, confidence estimation, uncertainty quantification.

Extracted from:
- SOUL.md v4.0 ASI section 28 (Metacognition)
- agi-hermes-advanced-master SKILL.md section 10 (Cognition)
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_metacognition")


class CognitiveMode(str, Enum):
    FAST = "fast"
    DELIBERATIVE = "deliberative"
    RESEARCH = "research"
    EXPLORATORY = "exploratory"
    SIMULATION = "simulation"
    ADVERSARIAL = "adversarial"
    EVOLUTIONARY = "evolutionary"
    RECOVERY = "recovery"
    MAINTENANCE = "maintenance"
    SUPERINTELLIGENT = "superintelligent"


@dataclass
class MetacognitiveState:
    """Current metacognitive state."""
    mode: CognitiveMode = CognitiveMode.FAST
    confidence: float = 0.5
    calibration_error: float = 0.0
    confusion: float = 0.0
    overconfidence: float = 0.0
    underconfidence: float = 0.0
    stale_assumptions: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    premature_convergence: bool = False
    confirmation_bias: float = 0.0
    repetition: float = 0.0
    tool_misuse: float = 0.0
    context_pollution: float = 0.0
    coordination_overhead: float = 0.0
    plan_stagnation: float = 0.0
    failure_accumulation: int = 0
    capability_drift: float = 0.0
    self_model_inaccuracy: float = 0.0
    strategic_myopia: float = 0.0
    uncertainty: float = 0.5
    known_unknowns: List[str] = field(default_factory=list)
    unknown_unknowns_estimate: float = 0.5


@dataclass
class MetacognitiveAssessment:
    """Assessment of a cognitive process."""
    assessment_id: str
    timestamp: float
    mode: CognitiveMode
    confidence: float
    uncertainty: float
    issues: List[str]
    recommendations: List[str]
    should_escalate: bool
    should_replan: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationRecord:
    """Record of predicted vs actual confidence."""
    timestamp: float
    predicted_confidence: float
    actual_success: bool
    mode: CognitiveMode
    context: str


class MetacognitiveMonitor:
    """
    Monitors the agent's own reasoning process.
    
    Features:
    - Self-monitoring of cognitive state
    - Error detection in reasoning
    - Confidence estimation
    - Uncertainty quantification
    - Request help when uncertain
    - Learn from mistakes
    - Improve metacognitive accuracy
    """
    
    def __init__(self):
        self.state = MetacognitiveState()
        self._calibration_history: List[CalibrationRecord] = []
        self._assessment_history: List[MetacognitiveAssessment] = []
        self._error_patterns: Dict[str, int] = {}
        self._improvement_suggestions: List[str] = []
    
    async def assess(
        self,
        mode: CognitiveMode,
        context: Dict[str, Any] = None
    ) -> MetacognitiveAssessment:
        """Assess the current cognitive state."""
        issues = []
        recommendations = []
        
        # Check for overconfidence
        if self.state.confidence > 0.9 and self.state.uncertainty > 0.3:
            issues.append("Overconfidence detected: high confidence but high uncertainty")
            recommendations.append("Reduce confidence or gather more evidence")
            self.state.overconfidence = 0.7
        
        # Check for underconfidence
        if self.state.confidence < 0.3 and self.state.uncertainty < 0.2:
            issues.append("Underconfidence detected: low confidence but low uncertainty")
            recommendations.append("Increase confidence based on evidence")
            self.state.underconfidence = 0.6
        
        # Check for confusion
        if self.state.confusion > 0.5:
            issues.append("High confusion detected")
            recommendations.append("Clarify objectives and constraints")
        
        # Check for premature convergence
        if self.state.premature_convergence:
            issues.append("Premature convergence: settling on answer too early")
            recommendations.append("Explore alternative hypotheses")
        
        # Check for confirmation bias
        if self.state.confirmation_bias > 0.6:
            issues.append("Confirmation bias: seeking only supporting evidence")
            recommendations.append("Actively seek disconfirming evidence")
        
        # Check for repetition
        if self.state.repetition > 0.5:
            issues.append("Repetition detected: repeating same actions")
            recommendations.append("Change strategy or approach")
        
        # Check for tool misuse
        if self.state.tool_misuse > 0.5:
            issues.append("Tool misuse: using wrong tools for the task")
            recommendations.append("Review tool selection criteria")
        
        # Check for context pollution
        if self.state.context_pollution > 0.5:
            issues.append("Context pollution: too much irrelevant information")
            recommendations.append("Compress and filter context")
        
        # Check for plan stagnation
        if self.state.plan_stagnation > 0.5:
            issues.append("Plan stagnation: plan not progressing")
            recommendations.append("Replan with new information")
        
        # Check for failure accumulation
        if self.state.failure_accumulation > 3:
            issues.append(f"Failure accumulation: {self.state.failure_accumulation} consecutive failures")
            recommendations.append("Escalate to human or change approach significantly")
        
        # Check for capability drift
        if self.state.capability_drift > 0.5:
            issues.append("Capability drift: performance degrading over time")
            recommendations.append("Recalibrate or retrain")
        
        # Check for self-model inaccuracy
        if self.state.self_model_inaccuracy > 0.5:
            issues.append("Self-model inaccuracy: model of self is inaccurate")
            recommendations.append("Update self-model based on recent performance")
        
        # Check for strategic myopia
        if self.state.strategic_myopia > 0.5:
            issues.append("Strategic myopia: focusing on short-term over long-term")
            recommendations.append("Expand planning horizon")
        
        # Determine if escalation needed
        should_escalate = (
            self.state.failure_accumulation > 5 or
            self.state.overconfidence > 0.8 or
            len(issues) > 5
        )
        
        # Determine if replanning needed
        should_replan = (
            self.state.plan_stagnation > 0.6 or
            self.state.confusion > 0.7 or
            self.state.premature_convergence
        )
        
        assessment = MetacognitiveAssessment(
            assessment_id=str(uuid.uuid4()),
            timestamp=time.time(),
            mode=mode,
            confidence=self.state.confidence,
            uncertainty=self.state.uncertainty,
            issues=issues,
            recommendations=recommendations,
            should_escalate=should_escalate,
            should_replan=should_replan,
            metadata={"issues_count": len(issues)}
        )
        
        self._assessment_history.append(assessment)
        
        return assessment
    
    def update_confidence(self, predicted: float, actual_success: bool, context: str = ""):
        """Update confidence calibration."""
        self._calibration_history.append(
            CalibrationRecord(
                timestamp=time.time(),
                predicted_confidence=predicted,
                actual_success=actual_success,
                mode=self.state.mode,
                context=context
            )
        )
        
        # Update calibration error
        if len(self._calibration_history) > 10:
            recent = self._calibration_history[-10:]
            errors = [
                abs(r.predicted_confidence - (1.0 if r.actual_success else 0.0))
                for r in recent
            ]
            self.state.calibration_error = sum(errors) / len(errors)
            
            # Adjust confidence based on calibration
            if self.state.calibration_error > 0.3:
                self.state.confidence *= 0.9  # Reduce confidence if poorly calibrated
    
    def estimate_confidence(self, evidence_count: int, source_quality: float, consistency: float) -> float:
        """Estimate confidence based on evidence."""
        # Base confidence from evidence count (diminishing returns)
        evidence_factor = 1.0 - math.exp(-evidence_count / 5.0)
        
        # Weighted combination
        raw_confidence = (
            evidence_factor * 0.4 +
            source_quality * 0.3 +
            consistency * 0.3
        )
        
        # Apply calibration correction
        if self.state.calibration_error > 0.2:
            raw_confidence *= (1.0 - self.state.calibration_error)
        
        self.state.confidence = min(1.0, max(0.0, raw_confidence))
        return self.state.confidence
    
    def quantify_uncertainty(
        self,
        known_unknowns: List[str] = None,
        evidence_gaps: List[str] = None,
        model_disagreement: float = 0.0
    ) -> Dict[str, float]:
        """Quantify uncertainty."""
        # Epistemic uncertainty (lack of knowledge)
        epistemic = len(known_unknowns or []) * 0.1 + len(evidence_gaps or []) * 0.05
        
        # Aleatoric uncertainty (inherent randomness)
        aleatoric = model_disagreement
        
        # Total uncertainty
        total = min(1.0, epistemic + aleatoric)
        
        self.state.uncertainty = total
        self.state.known_unknowns = known_unknowns or []
        
        return {
            "total": total,
            "epistemic": min(1.0, epistemic),
            "aleatoric": min(1.0, aleatoric),
            "known_unknowns_count": len(known_unknowns or []),
            "evidence_gaps_count": len(evidence_gaps or [])
        }
    
    def should_request_help(self, threshold: float = 0.7) -> Tuple[bool, str]:
        """Determine if human help should be requested."""
        reasons = []
        
        if self.state.uncertainty > threshold:
            reasons.append(f"High uncertainty: {self.state.uncertainty:.2f}")
        
        if self.state.failure_accumulation > 3:
            reasons.append(f"Multiple failures: {self.state.failure_accumulation}")
        
        if self.state.overconfidence > 0.8:
            reasons.append(f"Overconfidence detected: {self.state.overconfidence:.2f}")
        
        if len(self.state.missing_evidence) > 3:
            reasons.append(f"Missing evidence: {len(self.state.missing_evidence)} items")
        
        should_help = len(reasons) > 0
        reason_str = "; ".join(reasons) if reasons else "No help needed"
        
        return should_help, reason_str
    
    def learn_from_mistake(self, mistake_type: str, context: str = ""):
        """Learn from a mistake to improve future performance."""
        self._error_patterns[mistake_type] = self._error_patterns.get(mistake_type, 0) + 1
        
        # Generate improvement suggestion
        if self._error_patterns[mistake_type] > 2:
            suggestion = f"Pattern detected: '{mistake_type}' occurred {self._error_patterns[mistake_type]} times. Consider alternative approach."
            self._improvement_suggestions.append(suggestion)
            logger.warning("Metacognitive learning: %s", suggestion)
    
    def get_improvement_suggestions(self) -> List[str]:
        """Get improvement suggestions based on patterns."""
        return self._improvement_suggestions[-10:]  # Last 10 suggestions
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """Get calibration report."""
        if not self._calibration_history:
            return {"status": "no_data"}
        
        recent = self._calibration_history[-50:]
        accuracy = sum(1 for r in recent if r.actual_success) / len(recent)
        avg_predicted = sum(r.predicted_confidence for r in recent) / len(recent)
        
        return {
            "total_records": len(self._calibration_history),
            "recent_accuracy": accuracy,
            "average_predicted_confidence": avg_predicted,
            "calibration_error": self.state.calibration_error,
            "recommendation": "Well calibrated" if self.state.calibration_error < 0.2 else "Needs recalibration"
        }
    
    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "mode": self.state.mode.value,
            "confidence": self.state.confidence,
            "uncertainty": self.state.uncertainty,
            "calibration_error": self.state.calibration_error,
            "assessments_count": len(self._assessment_history),
            "error_patterns": len(self._error_patterns)
        }
