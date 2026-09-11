"""
SelfImprovement Engine — Autonomous continuous improvement loop for the harness.

Modules:
    analyzer   — ImprovementAnalyzer: analyze test results, code quality, agent perf
    optimizer  — AutoOptimizer: automatically optimize code based on analysis
    healer     — SelfHealer: detect and fix common issues automatically
    tracker    — PerformanceTracker: track improvements over time, A/B comparisons
    feedback   — FeedbackLoop: structured feedback collection from all agents
    evolution  — EvolutionEngine: drive the harness through continuous evolution cycles
"""

from .analyzer import ImprovementAnalyzer
from .optimizer import AutoOptimizer
from .healer import SelfHealer
from .tracker import PerformanceTracker
from .feedback import FeedbackLoop
from .evolution import EvolutionEngine

__version__ = "1.0.0"
__all__ = [
    "ImprovementAnalyzer",
    "AutoOptimizer",
    "SelfHealer",
    "PerformanceTracker",
    "FeedbackLoop",
    "EvolutionEngine",
]
