"""Core data models for the Engineering Metrics System."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"


class AccessLevel(str, Enum):
    READ_ONLY = "read_only"
    ANALYST = "analyst"
    ADMIN = "admin"


@dataclass
class MetricPoint:
    """A single metric observation with timestamp."""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class MetricWindow:
    """A collection of metric points within a time window, with trend."""

    name: str
    points: List[MetricPoint] = field(default_factory=list)
    window_seconds: float = 604800  # default 1 week

    def latest(self) -> Optional[MetricPoint]:
        if not self.points:
            return None
        return max(self.points, key=lambda p: p.timestamp)

    def average(self) -> float:
        if not self.points:
            return 0.0
        return sum(p.value for p in self.points) / len(self.points)

    def trend(self) -> TrendDirection:
        """Compute trend from first half vs second half of points."""
        if len(self.points) < 4:
            return TrendDirection.INSUFFICIENT_DATA
        mid = len(self.points) // 2
        first = sum(p.value for p in self.points[:mid]) / mid
        second = sum(p.value for p in self.points[mid:]) / (len(self.points) - mid)
        if second < first * 0.9:
            return TrendDirection.IMPROVING
        elif second > first * 1.1:
            return TrendDirection.DEGRADING
        return TrendDirection.STABLE

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "latest": self.latest().to_dict() if self.points else None,
            "average": round(self.average(), 4),
            "trend": self.trend().value,
            "count": len(self.points),
        }


@dataclass
class TeamHealthScore:
    """Aggregated team health score from pulse surveys."""

    overall_score: float  # 0-100
    dimensions: Dict[str, float] = field(default_factory=dict)
    survey_count: int = 0
    period_start: float = 0.0
    period_end: float = 0.0
    trends: Dict[str, TrendDirection] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 2),
            "dimensions": {k: round(v, 2) for k, v in self.dimensions.items()},
            "survey_count": self.survey_count,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "trends": {k: v.value for k, v in self.trends.items()},
        }


@dataclass
class PulseSurvey:
    """A single pulse survey response."""

    survey_id: str
    respondent: str
    timestamp: float = field(default_factory=time.time)
    scores: Dict[str, float] = field(default_factory=dict)  # dimension -> 1-5
    comments: str = ""
    period: str = "current"

    def to_dict(self) -> dict:
        return {
            "survey_id": self.survey_id,
            "respondent": self.respondent,
            "timestamp": self.timestamp,
            "scores": self.scores,
            "comments": self.comments,
            "period": self.period,
        }

    def average_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)