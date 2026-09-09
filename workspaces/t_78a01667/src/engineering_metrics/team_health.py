"""Team health survey framework with quarterly pulse surveys."""
from __future__ import annotations

import ast
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import PulseSurvey, TeamHealthScore, TrendDirection
from .storage import MetricsStorage


# Standard dimensions for team health surveys
DEFAULT_DIMENSIONS = [
    "satisfaction",
    "autonomy",
    "mastery",
    "purpose",
    "collaboration",
    "wellbeing",
]


class TeamHealthFramework:
    """Framework for collecting and analyzing team health pulse surveys.

    Dimensions are scored 1-5. The overall score maps to 0-100.
    """

    def __init__(self, storage: MetricsStorage, dimensions: List[str] = None) -> None:
        self._storage = storage
        self._dimensions = dimensions or list(DEFAULT_DIMENSIONS)

    @property
    def dimensions(self) -> List[str]:
        return list(self._dimensions)

    def create_survey(
        self,
        survey_id: str,
        respondent: str,
        scores: Dict[str, float],
        comments: str = "",
        period: str = "current",
        timestamp: Optional[float] = None,
    ) -> PulseSurvey:
        """Record a pulse survey response."""
        ts = timestamp or time.time()
        # Validate dimensions
        for dim in self._dimensions:
            if dim not in scores:
                scores[dim] = 0.0  # missing = 0, signals issue
        survey = PulseSurvey(
            survey_id=survey_id,
            respondent=respondent,
            timestamp=ts,
            period=period,
            scores=scores,
            comments=comments,
        )
        self._storage.insert_pulse_survey(survey)
        return survey

    def get_summary(
        self,
        since: Optional[float] = None,
        period: Optional[str] = None,
    ) -> TeamHealthScore:
        """Aggregate survey scores into a team health score."""
        now = time.time()
        if since is None:
            since = now - 90 * 86400  # last 90 days default

        surveys = self._storage.get_pulse_surveys(since, period=period)
        if not surveys:
            return TeamHealthScore(
                overall_score=0.0,
                survey_count=0,
                period_start=since,
                period_end=now,
            )

        # Average per dimension
        dim_sums: Dict[str, float] = defaultdict(float)
        dim_counts: Dict[str, int] = defaultdict(int)
        for s in surveys:
            scores = s.get("scores", {})
            if isinstance(scores, str):
                # Parse simple dict string representation
                try:
                    scores = eval(scores)  # noqa: S307 - trusted internal data
                except Exception:
                    continue
            for dim, val in scores.items():
                dim_sums[dim] += val
                dim_counts[dim] += 1

        dims: Dict[str, float] = {}
        for dim in self._dimensions:
            if dim_counts[dim] > 0:
                # Convert 1-5 scale to 0-100
                dims[dim] = (dim_sums[dim] / dim_counts[dim] / 5.0) * 100.0
            else:
                dims[dim] = 0.0

        overall = sum(dims.values()) / len(dims) if dims else 0.0

        # Trends: compare first half vs second half
        mid = len(surveys) // 2
        first_half = surveys[:mid] if mid > 0 else surveys
        second_half = surveys[mid:] if mid > 0 else []

        trends: Dict[str, TrendDirection] = {}
        if second_half:
            for dim in self._dimensions:
                first_avg = self._dim_avg(first_half, dim)
                second_avg = self._dim_avg(second_half, dim)
                if first_avg == 0:
                    trends[dim] = TrendDirection.INSUFFICIENT_DATA
                elif second_avg > first_avg * 1.05:
                    trends[dim] = TrendDirection.IMPROVING
                elif second_avg < first_avg * 0.95:
                    trends[dim] = TrendDirection.DEGRADING
                else:
                    trends[dim] = TrendDirection.STABLE
        else:
            for dim in self._dimensions:
                trends[dim] = TrendDirection.INSUFFICIENT_DATA

        return TeamHealthScore(
            overall_score=overall,
            dimensions=dims,
            survey_count=len(surveys),
            period_start=surveys[-1]["timestamp"] if surveys else since,
            period_end=now,
            trends=trends,
        )

    @staticmethod
    def _dim_avg(surveys: List[Dict], dim: str) -> float:
        vals = []
        for s in surveys:
            scores = s.get("scores", {})
            if isinstance(scores, str):
                try:
                    scores = ast.literal_eval(scores)  # noqa: S307
                except Exception:
                    continue
            if dim in scores:
                vals.append(scores[dim])
        return sum(vals) / len(vals) if vals else 0.0

    def generate_insights(self, score: TeamHealthScore) -> List[Dict]:
        """Generate actionable improvement insights from health scores."""
        insights: List[Dict] = []
        for dim, val in score.dimensions.items():
            if val < 40:
                insights.append({
                    "dimension": dim,
                    "score": round(val, 1),
                    "severity": "critical",
                    "action": f"Investigate {dim} - current score {val:.0f}/100 needs immediate attention",
                })
            elif val < 60:
                insights.append({
                    "dimension": dim,
                    "score": round(val, 1),
                    "severity": "warning",
                    "action": f"Monitor {dim} - score {val:.0f}/100, consider targeted interventions",
                })
            elif val < 75:
                insights.append({
                    "dimension": dim,
                    "score": round(val, 1),
                    "severity": "info",
                    "action": f"Maintain {dim} - score {val:.0f}/100, look for incremental improvements",
                })

        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        insights.sort(key=lambda x: severity_order.get(x["severity"], 3))
        return insights