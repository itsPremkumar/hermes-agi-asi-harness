"""
metacognition.py — Metacognition & Self-Monitoring Engine

Implements the agent's ability to reason about its own reasoning:
- Confidence calibration
- Strategy selection based on task type
- Self-evaluation of progress
- Bias detection and correction
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CognitiveMode(str, Enum):
    FAST = "fast"  # Familiar, low-risk, reversible
    DELIBERATIVE = "deliberative"  # Novel, consequential, conflicting
    EXPLORATORY = "exploratory"  # Open-ended discovery
    ADVERSARIAL = "adversarial"  # Security, verification, robustness
    REFLECTIVE = "reflective"  # After failures or surprises
    EXECUTIVE = "executive"  # Prioritization, resource allocation
    STRATEGIC = "strategic"  # Long-horizon foresight
    FORMAL = "formal"  # Symbolic + neural proof search


@dataclass
class ThinkingStep:
    step_number: int
    mode: CognitiveMode
    thought: str
    confidence: float  # 0.0 to 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class SelfModel:
    """Tracks the agent's self-assessment."""
    capabilities: dict[str, float] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    recent_failures: list[dict[str, Any]] = field(default_factory=list)
    recent_successes: list[dict[str, Any]] = field(default_factory=list)
    calibration_score: float = 0.5  # How well confidence tracks reality
    total_tasks_attempted: int = 0
    total_tasks_succeeded: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tasks_attempted == 0:
            return 0.0
        return self.total_tasks_succeeded / self.total_tasks_attempted


class MetacognitionEngine:
    """
    Metacognition engine for self-monitoring and strategy selection.
    """

    def __init__(self):
        self.self_model = SelfModel()
        self.thinking_history: list[ThinkingStep] = []
        self._current_mode = CognitiveMode.DELIBERATIVE

    def select_mode(self, task_description: str, context: dict[str, Any] | None = None) -> CognitiveMode:
        """Selects the best cognitive mode for a task."""
        task_lower = task_description.lower()

        if any(w in task_lower for w in ["verify", "security", "audit", "check", "test"]):
            mode = CognitiveMode.ADVERSARIAL
        elif any(w in task_lower for w in ["research", "discover", "explore", "find"]):
            mode = CognitiveMode.EXPLORATORY
        elif any(w in task_lower for w in ["plan", "strategy", "long-term", "roadmap"]):
            mode = CognitiveMode.STRATEGIC
        elif any(w in task_lower for w in ["prove", "theorem", "formal", "invariant"]):
            mode = CognitiveMode.FORMAL
        elif any(w in task_lower for w in ["fix", "debug", "repair", "recover"]):
            mode = CognitiveMode.REFLECTIVE
        elif any(w in task_lower for w in ["simple", "quick", "small", "trivial"]):
            mode = CognitiveMode.FAST
        else:
            mode = CognitiveMode.DELIBERATIVE

        self._current_mode = mode
        return mode

    def evaluate_confidence(self, task: str, proposed_answer: str, evidence: list[str]) -> float:
        """
        Evaluates confidence in a proposed answer based on evidence quality.
        Returns a calibrated confidence score between 0 and 1.
        """
        if not evidence:
            return 0.3  # Low confidence without evidence

        # Base confidence from evidence count
        base = min(0.9, 0.4 + len(evidence) * 0.1)

        # Adjust for evidence quality (length as proxy)
        quality_bonus = min(0.2, sum(len(e) for e in evidence) / 1000)

        # Calibrate based on historical accuracy
        calibration = self.self_model.calibration_score

        confidence = min(1.0, base + quality_bonus) * (0.5 + 0.5 * calibration)
        return round(min(1.0, confidence), 2)

    def record_thought(self, thought: str, confidence: float) -> ThinkingStep:
        """Records a thinking step for later reflection."""
        step = ThinkingStep(
            step_number=len(self.thinking_history) + 1,
            mode=self._current_mode,
            thought=thought,
            confidence=confidence,
        )
        self.thinking_history.append(step)
        return step

    def record_outcome(self, task: str, success: bool, error: str | None = None):
        """Records task outcome for self-model updating."""
        self.self_model.total_tasks_attempted += 1
        if success:
            self.self_model.total_tasks_succeeded += 1
            self.self_model.recent_successes.append({
                "task": task,
                "timestamp": time.time(),
            })
        else:
            self.self_model.recent_failures.append({
                "task": task,
                "error": error,
                "timestamp": time.time(),
            })

        # Update calibration (simple exponential moving average)
        if self.self_model.total_tasks_attempted > 0:
            actual = 1.0 if success else 0.0
            predicted = self.self_model.calibration_score
            self.self_model.calibration_score = 0.9 * predicted + 0.1 * actual

    def get_reflection(self) -> dict[str, Any]:
        """Generates a self-reflection summary."""
        recent_failures = len([f for f in self.self_model.recent_failures
                              if time.time() - f.get("timestamp", 0) < 3600])
        recent_successes = len([s for s in self.self_model.recent_successes
                               if time.time() - s.get("timestamp", 0) < 3600])

        return {
            "success_rate": self.self_model.success_rate,
            "calibration": self.self_model.calibration_score,
            "recent_failures_last_hour": recent_failures,
            "recent_successes_last_hour": recent_successes,
            "current_mode": self._current_mode.value,
            "total_thinking_steps": len(self.thinking_history),
            "recommendation": self._generate_recommendation(),
        }

    def _generate_recommendation(self) -> str:
        """Generates a recommendation based on self-assessment."""
        if self.self_model.success_rate < 0.5:
            return "Consider using more DELIBERATIVE mode and gathering more evidence before concluding."
        elif self.self_model.calibration_score < 0.6:
            return "Confidence calibration needs improvement — track predictions vs outcomes more carefully."
        elif len(self.self_model.recent_failures) > 5:
            return "High recent failure rate — consider switching to REFLECTIVE mode and analyzing patterns."
        else:
            return "Operating within normal parameters."

    def should_delegate(self, task_description: str) -> bool:
        """Decides if a task should be delegated to a subagent."""
        # Delegate if task is complex and we're not already in a delegated context
        indicators = ["research", "analyze", "compare", "investigate", "comprehensive"]
        return any(w in task_description.lower() for w in indicators)


async def create(kernel=None) -> MetacognitionEngine:
    """Factory function for kernel integration."""
    engine = MetacognitionEngine()
    return engine
