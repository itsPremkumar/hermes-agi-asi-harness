"""Feedback Engine — per-node validation, multi-round verification pipeline, self-critique."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from ..errors import FeedbackError

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    score: float = 0.0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CritiqueResult:
    """Result of a self-critique."""

    original: str
    revised: str
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    score: float = 0.0


class NodeValidator:
    """Validates node outputs."""

    def __init__(self, rules: Optional[list[dict[str, Any]]] = None) -> None:
        self.rules = rules or []

    def add_rule(self, name: str, check: callable, weight: float = 1.0) -> None:
        self.rules.append({"name": name, "check": check, "weight": weight})

    def validate(self, output: Any) -> ValidationResult:
        if not self.rules:
            return ValidationResult(passed=True, score=1.0)

        total_score = 0.0
        total_weight = 0.0
        messages = []

        for rule in self.rules:
            try:
                passed = rule["check"](output)
                if passed:
                    total_score += rule["weight"]
                else:
                    messages.append(f"Rule '{rule['name']}' failed")
            except Exception as e:
                messages.append(f"Rule '{rule['name']}' error: {e}")
            total_weight += rule["weight"]

        score = total_score / total_weight if total_weight > 0 else 0.0
        return ValidationResult(
            passed=score >= 0.7,
            score=score,
            message="; ".join(messages) if messages else "All rules passed",
        )


class VerificationPipeline:
    """Multi-round verification pipeline."""

    def __init__(self, max_rounds: int = 3, min_score: float = 0.8) -> None:
        self.max_rounds = max_rounds
        self.min_score = min_score
        self._validators: list[NodeValidator] = []

    def add_validator(self, validator: NodeValidator) -> None:
        self._validators.append(validator)

    def verify(self, output: Any) -> tuple[bool, list[ValidationResult]]:
        results = []
        for round_num in range(self.max_rounds):
            round_results = []
            for validator in self._validators:
                result = validator.validate(output)
                round_results.append(result)
            results.extend(round_results)
            avg_score = sum(r.score for r in round_results) / len(round_results) if round_results else 0
            if avg_score >= self.min_score:
                return True, results
        return False, results


class SelfCritique:
    """Self-critique mechanism."""

    def __init__(self, critique_fn: Optional[callable] = None) -> None:
        self.critique_fn = critique_fn or self._default_critique

    def _default_critique(self, text: str) -> CritiqueResult:
        issues = []
        suggestions = []
        if len(text) < 10:
            issues.append("Output too short")
            suggestions.append("Provide more detail")
        if not text.strip():
            issues.append("Empty output")
            suggestions.append("Generate meaningful content")
        score = max(0.0, 1.0 - len(issues) * 0.3)
        return CritiqueResult(
            original=text,
            revised=text,
            issues=issues,
            suggestions=suggestions,
            score=score,
        )

    def critique(self, text: str) -> CritiqueResult:
        return self.critique_fn(text)

    def critique_and_revise(self, text: str, max_iterations: int = 3) -> CritiqueResult:
        current = text
        for _ in range(max_iterations):
            result = self.critique(current)
            if result.score >= 0.8:
                return result
            current = result.revised
        return self.critique(current)


class FeedbackEngine:
    """Main feedback engine combining validation, verification, and self-critique."""

    def __init__(self) -> None:
        self.validators: dict[str, NodeValidator] = {}
        self.pipelines: dict[str, VerificationPipeline] = {}
        self.critique = SelfCritique()

    def register_validator(self, node_id: str, validator: NodeValidator) -> None:
        self.validators[node_id] = validator

    def register_pipeline(self, name: str, pipeline: VerificationPipeline) -> None:
        self.pipelines[name] = pipeline

    def validate_node(self, node_id: str, output: Any) -> ValidationResult:
        validator = self.validators.get(node_id)
        if validator is None:
            return ValidationResult(passed=True, score=1.0, message="No validator registered")
        return validator.validate(output)

    def verify_with_pipeline(self, name: str, output: Any) -> tuple[bool, list[ValidationResult]]:
        pipeline = self.pipelines.get(name)
        if pipeline is None:
            return True, []
        return pipeline.verify(output)

    def critique_output(self, text: str) -> CritiqueResult:
        return self.critique.critique(text)
