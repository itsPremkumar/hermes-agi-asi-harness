#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v6.0 — FEEDBACK LEARNER
================================================
Continuous learning from feedback.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_feedback")


@dataclass
class FeedbackRecord:
    """A feedback record."""
    feedback_id: str
    feedback_type: str  # explicit, implicit
    rating: float  # 0-1
    context: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


class FeedbackLearner:
    """Continuous learning from feedback."""
    
    def __init__(self):
        self._feedback_history: list[FeedbackRecord] = []
        self._ab_tests: dict[str, dict[str, Any]] = {}
        self._learning_curves: dict[str, list[float]] = {}
        self._drift_detector: dict[str, Any] = {"baseline": 0.5, "current": 0.5}
    
    def collect_explicit(self, rating: float, context: str = "") -> str:
        """Collect explicit feedback."""
        record = FeedbackRecord(
            feedback_id=str(uuid.uuid4()),
            feedback_type="explicit",
            rating=rating,
            context=context,
            timestamp=time.time()
        )
        self._feedback_history.append(record)
        return record.feedback_id
    
    def collect_implicit(self, success: bool, context: str = "") -> str:
        """Collect implicit feedback."""
        record = FeedbackRecord(
            feedback_id=str(uuid.uuid4()),
            feedback_type="implicit",
            rating=1.0 if success else 0.0,
            context=context,
            timestamp=time.time()
        )
        self._feedback_history.append(record)
        return record.feedback_id
    
    def start_ab_test(self, test_name: str, variant_a: str, variant_b: str) -> str:
        """Start an A/B test."""
        test_id = str(uuid.uuid4())
        self._ab_tests[test_id] = {
            "name": test_name,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "results_a": [],
            "results_b": [],
            "status": "running"
        }
        return test_id
    
    def record_ab_result(self, test_id: str, variant: str, success: bool):
        """Record A/B test result."""
        if test_id in self._ab_tests:
            key = f"results_{variant}"
            if key in self._ab_tests[test_id]:
                self._ab_tests[test_id][key].append(1.0 if success else 0.0)
    
    def get_ab_result(self, test_id: str) -> dict[str, Any]:
        """Get A/B test result."""
        test = self._ab_tests.get(test_id)
        if not test:
            return {"error": "Test not found"}
        
        avg_a = sum(test["results_a"]) / len(test["results_a"]) if test["results_a"] else 0
        avg_b = sum(test["results_b"]) / len(test["results_b"]) if test["results_b"] else 0
        
        return {
            "test_name": test["name"],
            "variant_a_avg": avg_a,
            "variant_b_avg": avg_b,
            "winner": "a" if avg_a > avg_b else "b",
            "confidence": abs(avg_a - avg_b)
        }
    
    def detect_drift(self, metric_name: str, current_value: float) -> bool:
        """Detect concept drift."""
        baseline = self._drift_detector.get("baseline", 0.5)
        drift = abs(current_value - baseline)
        
        if drift > 0.2:
            logger.warning("Concept drift detected: %.2f -> %.2f", baseline, current_value)
            self._drift_detector["current"] = current_value
            return True
        return False
    
    def get_learning_curve(self, metric_name: str) -> list[float]:
        """Get learning curve for a metric."""
        return self._learning_curves.get(metric_name, [])
    
    async def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "feedback_count": len(self._feedback_history),
            "ab_tests": len(self._ab_tests)
        }
