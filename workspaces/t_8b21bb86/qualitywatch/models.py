"""QualityWatch — Data Quality Monitoring & Validation System.

Core domain model: datasets, rules, profiles, checks, and results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Status(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class Rule:
    """A data-quality rule."""
    name: str
    rule_type: str                      # null_check | uniqueness | range | referential | custom
    column: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    severity: Severity = Severity.ERROR
    enabled: bool = True

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Rule name is required")
        if self.rule_type not in {"null_check", "uniqueness", "range", "referential", "custom"}:
            raise ValueError(f"Unknown rule type: {self.rule_type}")


@dataclass
class CheckResult:
    """Result of running one rule against one dataset."""
    rule_name: str
    rule_type: str
    status: Status
    severity: Severity
    message: str
    rows_affected: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityProfile:
    """Statistical profile of a dataset."""
    dataset_name: str
    row_count: int = 0
    column_count: int = 0
    null_counts: dict[str, int] = field(default_factory=dict)
    uniqueness: dict[str, float] = field(default_factory=dict)
    stats: dict[str, dict[str, float]] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)