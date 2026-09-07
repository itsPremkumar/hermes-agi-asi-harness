"""CodeReview System — autonomous code review agent.

Reviews code changes against quality standards, security, and harness conventions.
"""

from __future__ import annotations

from .engine import ReviewEngine, ReviewResult, ReviewSeverity
from .quality import QualityChecker, QualityReport, QualityIssue
from .security import SecurityScanner, SecurityReport, Vulnerability
from .convention import ConventionEnforcer, ConventionViolation
from .reporter import ReviewReporter
from .autofix import AutoFixer, FixResult

__all__ = [
    "AutoFixer",
    "ConventionEnforcer",
    "ConventionViolation",
    "FixResult",
    "QualityChecker",
    "QualityIssue",
    "QualityReport",
    "ReviewEngine",
    "ReviewReporter",
    "ReviewResult",
    "ReviewSeverity",
    "SecurityReport",
    "SecurityScanner",
    "Vulnerability",
]
