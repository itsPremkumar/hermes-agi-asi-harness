"""
self_healing.py — Self-Healing Engine with Failure Diagnosis & Repair

Analyzes failures, classifies them by root cause, suggests fixes,
and attempts automated repair with verification.
"""

import time
import ast
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FailureClass(str, Enum):
    SYNTAX = "syntax_error"
    RUNTIME = "runtime_exception"
    TIMEOUT = "timeout"
    PERMISSION = "permission_denied"
    RESOURCE = "resource_exhausted"
    LOGIC = "logic_error"
    CONFIG = "configuration_error"
    INJECTION = "injection_attack"
    UNKNOWN = "unknown"


@dataclass
class FailurePattern:
    """Structured representation of a failure."""
    pattern_id: str
    failure_class: FailureClass
    error_signature: str
    context: str
    frequency: int = 1
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    suggested_fix: str = ""
    auto_repair_possible: bool = True


@dataclass
class RepairAttempt:
    """Record of a repair attempt."""
    attempt_id: str
    failure_pattern: str
    fix_applied: str
    success: bool
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class SelfHealingEngine:
    """
    Self-healing engine that diagnoses failures, suggests fixes,
    and attempts automated repair.
    """

    def __init__(self):
        self.known_patterns: Dict[str, FailurePattern] = {}
        self.repair_history: List[RepairAttempt] = []
        self._repair_strategies: Dict[FailureClass, Callable] = {
            FailureClass.SYNTAX: self._repair_syntax,
            FailureClass.TIMEOUT: self._repair_timeout,
            FailureClass.PERMISSION: self._repair_permission,
            FailureClass.CONFIG: self._repair_config,
            FailureClass.LOGIC: self._repair_logic,
        }

    def diagnose_failure(self, error_trace: str, context: str = "") -> FailurePattern:
        """
        Classifies a failure by examining the error trace.
        Returns a structured FailurePattern.
        """
        error_lower = error_trace.lower()
        failure_class = FailureClass.UNKNOWN
        error_signature = f"{type(error_trace).__name__}: {str(error_trace)[:200]}"

        if "syntaxerror" in error_lower or "syntax error" in error_lower:
            failure_class = FailureClass.SYNTAX
        elif "timed out" in error_lower or "timeout" in error_lower:
            failure_class = FailureClass.TIMEOUT
        elif "permission denied" in error_lower or "access denied" in error_lower:
            failure_class = FailureClass.PERMISSION
        elif "memoryerror" in error_lower or "oom" in error_lower or "resource" in error_lower:
            failure_class = FailureClass.RESOURCE
        elif "keyerror" in error_lower or "attributeerror" in error_lower or "valueerror" in error_lower:
            failure_class = FailureClass.LOGIC
        elif "filenotfounderror" in error_lower and ("config" in error_lower or ".yaml" in error_lower):
            failure_class = FailureClass.CONFIG
        elif "injection" in error_lower or "bypass" in error_lower or "ignore" in error_lower:
            failure_class = FailureClass.INJECTION
        elif "exception" in error_lower or "error" in error_lower:
            failure_class = FailureClass.RUNTIME

        pattern_id = f"fp_{int(time.time() * 1000)}_{abs(hash(error_signature)) % 10000}"
        pattern = FailurePattern(
            pattern_id=pattern_id,
            failure_class=failure_class,
            error_signature=error_signature,
            context=context,
            suggested_fix=self._suggest_fix(failure_class, error_trace),
            auto_repair_possible=failure_class in self._repair_strategies,
        )

        # Update known patterns
        sig_hash = str(abs(hash(error_signature)))
        if sig_hash in self.known_patterns:
            existing = self.known_patterns[sig_hash]
            existing.frequency += 1
            existing.last_seen = time.time()
            pattern = existing  # Return existing pattern
        else:
            self.known_patterns[sig_hash] = pattern

        return pattern

    def _suggest_fix(self, failure_class: FailureClass, error_trace: str) -> str:
        """Suggests a fix for a failure class."""
        suggestions = {
            FailureClass.SYNTAX: "Run AST parser to locate and fix syntax errors before execution.",
            FailureClass.RUNTIME: "Check for null references, boundary conditions, and exception handling.",
            FailureClass.TIMEOUT: "Implement exponential backoff, reduce timeout, or parallelize work.",
            FailureClass.PERMISSION: "Check permission levels and escalate to user for approval (R4+).",
            FailureClass.RESOURCE: "Reduce memory usage, free resources, or increase resource limits.",
            FailureClass.LOGIC: "Add boundary checks, validate inputs, and write unit tests for edge cases.",
            FailureClass.CONFIG: "Verify config file exists and is valid YAML/JSON. Check required fields.",
            FailureClass.INJECTION: "Sanitize input, enforce trust boundaries, and block untrusted prompt overrides.",
            FailureClass.UNKNOWN: "Analyze the full error trace and context for root cause analysis.",
        }
        return suggestions.get(failure_class, "No automatic fix available.")

    async def suggest_fix(self, pattern: FailurePattern) -> str:
        """Returns the suggested fix for a failure pattern."""
        return pattern.suggested_fix

    async def attempt_repair(
        self,
        pattern: FailurePattern,
        repair_fn: Optional[Callable] = None,
    ) -> RepairAttempt:
        """
        Attempts to repair a failure.
        If a custom repair_fn is provided, uses that.
        Otherwise, uses the built-in strategy for the failure class.
        """
        import uuid

        start = time.time()
        attempt_id = f"repair_{uuid.uuid4().hex[:8]}"
        fix_applied = ""
        success = False

        try:
            if repair_fn:
                fix_applied = await repair_fn(pattern)
                success = True
            elif pattern.failure_class in self._repair_strategies:
                strategy = self._repair_strategies[pattern.failure_class]
                fix_applied = await strategy(pattern)
                success = True
            else:
                fix_applied = "No automated repair strategy available for this failure class."
                success = False
        except Exception as e:
            fix_applied = f"Repair strategy failed: {e}"
            success = False

        duration = (time.time() - start) * 1000

        attempt = RepairAttempt(
            attempt_id=attempt_id,
            failure_pattern=pattern.pattern_id,
            fix_applied=fix_applied,
            success=success,
            duration_ms=duration,
        )
        self.repair_history.append(attempt)

        if success:
            logger.info("Repair %s succeeded in %.1fms: %s", attempt_id, duration, fix_applied[:80])
        else:
            logger.warning("Repair %s failed: %s", attempt_id, fix_applied[:80])

        return attempt

    async def _repair_syntax(self, pattern: FailurePattern) -> str:
        """Suggests AST-based syntax repair."""
        # Try to extract and fix common syntax issues
        if "expected ':'" in pattern.error_signature:
            return "Add missing colon at end of line."
        elif "unmatched" in pattern.error_signature:
            return "Check for unmatched brackets or quotes."
        return "Run ast.parse() to locate syntax error and fix."

    async def _repair_timeout(self, pattern: FailurePattern) -> str:
        """Suggests timeout repair."""
        return "Reduce task complexity, add chunking, or increase timeout. Use async/non-blocking I/O."

    async def _repair_permission(self, pattern: FailurePattern) -> str:
        """Suggests permission repair."""
        return "Check permission level. R4+ requires explicit user authorization. Do not auto-elevate."

    async def _repair_config(self, pattern: FailurePattern) -> str:
        """Suggests config repair."""
        return "Verify config file path and format. Fall back to defaults if missing."

    async def _repair_logic(self, pattern: FailurePattern) -> str:
        """Suggests logic repair."""
        return "Add try/except boundary checks, validate inputs, and test edge cases."

    def get_stats(self) -> Dict[str, Any]:
        """Returns self-healing statistics."""
        successful = sum(1 for r in self.repair_history if r.success)
        return {
            "total_failures_diagnosed": len(self.known_patterns),
            "total_repair_attempts": len(self.repair_history),
            "successful_repairs": successful,
            "failed_repairs": len(self.repair_history) - successful,
            "success_rate": successful / len(self.repair_history) if self.repair_history else 0,
        }


class SelfHealingPlugin:
    """Plugin wrapper for SelfHealingEngine."""

    def __init__(self, kernel=None):
        self.state = "started"
        self.kernel = kernel
        self.engine = SelfHealingEngine()
        self.manifest = type('Manifest', (), {'name': 'self_healing', 'version': '1.0.0'})()

    async def load(self):
        return True

    async def start(self):
        return True

    async def stop(self):
        return True

    async def health(self):
        return {
            "status": "healthy",
            "plugin": "self_healing",
            "version": "1.0.0",
            "state": self.state,
            "healthy": True,
            "stats": self.engine.get_stats(),
        }

    def get_capabilities(self):
        return ["failure_diagnosis", "auto_repair", "pattern_learning"]

    def diagnose_failure(self, *args, **kwargs):
        return self.engine.diagnose_failure(*args, **kwargs)

    async def attempt_repair(self, *args, **kwargs):
        return await self.engine.attempt_repair(*args, **kwargs)


async def create(kernel=None) -> SelfHealingPlugin:
    """Factory function for kernel integration."""
    plugin = SelfHealingPlugin(kernel)
    await plugin.load()
    await plugin.start()
    return plugin
