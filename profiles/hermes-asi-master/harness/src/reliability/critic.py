#!/usr/bin/env python3
"""
critic.py — Red-Team Adversarial Critic & Failure Intelligence Extractor
Analyzes failure modes, extracts structured lessons, and formulates preventative invariants.
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class FailureLesson:
    id: str
    task_description: str
    error_trace: str
    root_cause: str
    prevention_rule: str
    timestamp: float = field(default_factory=time.time)

class RedTeamCritic:
    def __init__(self):
        self.lessons_learned: List[FailureLesson] = []

    def critique_plan(self, plan_steps: List[str]) -> List[str]:
        """Critiques a plan for common failure modes (missing verification, no rollback, etc.)."""
        critiques = []
        has_verify = any("verify" in s.lower() or "test" in s.lower() for s in plan_steps)
        if not has_verify:
            critiques.append("CRITIQUE: Plan lacks an explicit verification and testing step.")

        if len(plan_steps) < 2:
            critiques.append("CRITIQUE: Plan is too brief; needs decomposition into verifiable sub-phases.")

        return critiques

    def extract_failure_lesson(self, task: str, error_trace: str) -> FailureLesson:
        """Extracts structured diagnostic lesson from a failure."""
        lesson_id = f"lesson_{int(time.time() * 1000)}"
        root_cause = "Runtime / Logic Exception"
        prevention_rule = "Add boundary checks and unit tests for error condition."

        if "timeout" in error_trace.lower():
            root_cause = "Subprocess / API Timeout Exceeded"
            prevention_rule = "Implement exponential backoff and verify async non-blocking execution."
        elif "syntax" in error_trace.lower():
            root_cause = "AST Syntax Error in generated code"
            prevention_rule = "Run AST parser prior to execution."
        elif "secret" in error_trace.lower():
            root_cause = "Hardcoded token leak attempt"
            prevention_rule = "Enforce R0 regex scan before disk write."

        lesson = FailureLesson(
            id=lesson_id,
            task_description=task,
            error_trace=error_trace[:500],
            root_cause=root_cause,
            prevention_rule=prevention_rule
        )
        self.lessons_learned.append(lesson)
        return lesson
