
"""
Cognitive Router — 10 cognitive modes for different mission types.

Extracted from SKILL.md v9.0 ASI section 10:
- FAST, DELIBERATIVE, RESEARCH, EXPLORATORY, SIMULATION
- ADVERSARIAL, EVOLUTIONARY, RECOVERY, MAINTENANCE, SUPERINTELLIGENT
"""

from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


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
class CognitiveState:
    """Current cognitive state."""
    mode: CognitiveMode = CognitiveMode.FAST
    confidence: float = 0.5
    confusion: float = 0.0
    overconfidence: float = 0.0
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


class CognitiveRouter:
    """
    Routes tasks to appropriate cognitive mode.
    
    Monitors for:
    - Goal drift, confusion, overconfidence
    - Stale assumptions, missing evidence
    - Premature convergence, confirmation bias
    - Repetition, tool misuse, context pollution
    - Coordination overhead, plan stagnation
    - Failure accumulation, capability drift
    - Self-model inaccuracy, strategic myopia
    """

    MODE_DESCRIPTIONS = {
        CognitiveMode.FAST: "Routine, reversible, known — minimal reasoning",
        CognitiveMode.DELIBERATIVE: "Novel, high-impact, conflicting — extended reasoning",
        CognitiveMode.RESEARCH: "High uncertainty, needs facts — evidence synthesis",
        CognitiveMode.EXPLORATORY: "Unknown environment — hypothesis generation",
        CognitiveMode.SIMULATION: "Risky but simulable — ensemble simulation",
        CognitiveMode.ADVERSARIAL: "Security, verification, high stakes — red-team",
        CognitiveMode.EVOLUTIONARY: "Optimization with evaluators — variant generation",
        CognitiveMode.RECOVERY: "Failure diagnosis — causal analysis",
        CognitiveMode.MAINTENANCE: "Background consolidation — memory, index, skill",
        CognitiveMode.SUPERINTELLIGENT: "Strategic, cross-domain, foresight — scenario trees",
    }

    def __init__(self):
        self.state = CognitiveState()
        self._mode_history: List[CognitiveMode] = []

    def select_mode(self, task: str, context: Dict[str, Any] = None) -> CognitiveMode:
        """Select the appropriate cognitive mode for a task."""
        task_lower = task.lower()

        # Determine mode based on task characteristics
        if any(w in task_lower for w in ["research", "find", "search", "investigate"]):
            mode = CognitiveMode.RESEARCH
        elif any(w in task_lower for w in ["analyze", "evaluate", "assess", "compare"]):
            mode = CognitiveMode.DELIBERATIVE
        elif any(w in task_lower for w in ["create", "build", "implement", "code"]):
            mode = CognitiveMode.EXPLORATORY
        elif any(w in task_lower for w in ["verify", "validate", "prove", "test"]):
            mode = CognitiveMode.ADVERSARIAL
        elif any(w in task_lower for w in ["optimize", "improve", "evolve", "refine"]):
            mode = CognitiveMode.EVOLUTIONARY
        elif any(w in task_lower for w in ["fix", "debug", "recover", "repair"]):
            mode = CognitiveMode.RECOVERY
        elif any(w in task_lower for w in ["consolidate", "index", "maintain", "clean"]):
            mode = CognitiveMode.MAINTENANCE
        elif any(w in task_lower for w in ["strategic", "forecast", "scenario", "future"]):
            mode = CognitiveMode.SUPERINTELLIGENT
        elif any(w in task_lower for w in ["simulate", "model", "predict"]):
            mode = CognitiveMode.SIMULATION
        else:
            mode = CognitiveMode.FAST

        self._mode_history.append(mode)
        self.state.mode = mode
        return mode

    def get_mode_description(self, mode: CognitiveMode) -> str:
        """Get description of a cognitive mode."""
        return self.MODE_DESCRIPTIONS.get(mode, "Unknown mode")

    def monitor(self) -> Dict[str, Any]:
        """Monitor cognitive state for issues."""
        issues = []

        if self.state.overconfidence > 0.7:
            issues.append("Overconfidence detected — reduce confidence")
        if self.state.confusion > 0.5:
            issues.append("Confusion detected — clarify objectives")
        if self.state.premature_convergence:
            issues.append("Premature convergence — explore alternatives")
        if self.state.confirmation_bias > 0.6:
            issues.append("Confirmation bias — seek disconfirming evidence")
        if self.state.repetition > 0.5:
            issues.append("Repetition detected — change strategy")
        if self.state.tool_misuse > 0.5:
            issues.append("Tool misuse — review tool selection")
        if self.state.context_pollution > 0.5:
            issues.append("Context pollution — compress context")
        if self.state.plan_stagnation > 0.5:
            issues.append("Plan stagnation — replan")
        if self.state.failure_accumulation > 3:
            issues.append("Failure accumulation — escalate")
        if self.state.capability_drift > 0.5:
            issues.append("Capability drift — recalibrate")
        if self.state.self_model_inaccuracy > 0.5:
            issues.append("Self-model inaccuracy — update self-model")
        if self.state.strategic_myopia > 0.5:
            issues.append("Strategic myopia — expand horizon")

        return {
            "mode": self.state.mode.value,
            "issues": issues,
            "issue_count": len(issues),
        }

    def reflect(self) -> Dict[str, Any]:
        """Reflect on cognitive state and adjust."""
        monitor_result = self.monitor()

        # Auto-correct based on issues
        if monitor_result["issue_count"] > 3:
            # Switch to deliberative mode if too many issues
            self.state.mode = CognitiveMode.DELIBERATIVE
            logger.info("Auto-switched to DELIBERATIVE mode due to %d issues", monitor_result["issue_count"])

        return monitor_result
