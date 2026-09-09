"""DORA metrics: Deployment Frequency, Lead Time, MTTR, Change Fail Rate."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import MetricPoint, MetricWindow, TrendDirection
from .storage import MetricsStorage


@dataclass
class DeploymentRecord:
    """A deployment event."""

    repo: str
    env: str  # 'prod', 'staging', etc.
    timestamp: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class ChangeRecord:
    """A code change / PR with lead time and failure status."""

    repo: str
    lead_time_hours: float
    failed: bool = False
    PR_number: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class DORAMetrics:
    """Computed DORA metrics over a window."""

    deployment_frequency: float  # deployments per week
    lead_time_median_hours: float  # median lead time hours
    lead_time_p95_hours: float  # p95 lead time hours
    mttr_hours: float  # mean time to resolve (hours)
    change_fail_rate: float  # 0-1, fraction of failed changes
    trend: TrendDirection = TrendDirection.STABLE
    windows: Dict[str, MetricWindow] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "deployment_frequency_per_week": round(self.deployment_frequency, 4),
            "lead_time_median_hours": round(self.lead_time_median_hours, 2),
            "lead_time_p95_hours": round(self.lead_time_p95_hours, 2),
            "mttr_hours": round(self.mttr_hours, 2),
            "change_fail_rate": round(self.change_fail_rate, 4),
            "trend": self.trend.value,
            "windows": {k: w.to_dict() for k, w in self.windows.items()},
        }


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(s):
        return s[-1]
    return s[f] + (k - f) * (s[c] - s[f])


class DORACompute:
    """Compute DORA metrics from storage."""

    def __init__(self, storage: MetricsStorage) -> None:
        self._storage = storage

    def compute(
        self, weeks: int = 4, prev_weeks: int = 4
    ) -> DORAMetrics:
        """Compute DORA metrics for the last *weeks* vs previous *prev_weeks*."""
        now = time.time()
        week_sec = 604800

        cur_since = now - weeks * week_sec
        prev_since = cur_since - prev_weeks * week_sec
        prev_until = cur_since

        cur_deps = self._storage.get_deployments(cur_since)
        prev_deps = self._storage.get_deployments(prev_since) if prev_since > 0 else []

        cur_changes = self._storage.get_changes(cur_since)
        prev_changes = self._storage.get_changes(prev_since, cur_since)

        cur_incidents = self._storage.get_incidents(cur_since)
        prev_incidents = self._storage.get_incidents(prev_since)

        # --- Deployment frequency (per week) ---
        cur_freq = len(cur_deps) / weeks if weeks else 0.0
        prev_freq = len(prev_deps) / prev_weeks if prev_weeks else 0.0
        freq_window = MetricWindow(
            "deployment_frequency",
            [MetricPoint("df", cur_freq, now), MetricPoint("df", prev_freq, prev_until)],
        )

        # --- Lead time ---
        cur_lead_times = [c["lead_time_hours"] for c in cur_changes if c.get("lead_time_hours", 0) > 0]
        prev_lead_times = [c["lead_time_hours"] for c in prev_changes if c.get("lead_time_hours", 0) > 0]
        lead_median = _median(cur_lead_times)
        lead_p95 = _percentile(cur_lead_times, 95) if cur_lead_times else 0.0
        lead_window = MetricWindow(
            "lead_time_hours",
            [
                MetricPoint("lt_median", lead_median, now),
                MetricPoint("lt_median", _median(prev_lead_times), prev_until),
            ],
        )

        # --- MTTR ---
        cur_mttr = self._avg_mttr(cur_incidents)
        prev_mttr = self._avg_mttr(prev_incidents)
        mttr_window = MetricWindow(
            "mttr_hours",
            [
                MetricPoint("mttr", cur_mttr, now),
                MetricPoint("mttr", prev_mttr, prev_until),
            ],
        )

        # --- Change fail rate ---
        cur_fail = sum(1 for c in cur_changes if c.get("failed", False))
        cur_total = len(cur_changes) or 1
        prev_fail = sum(1 for c in prev_changes if c.get("failed", False))
        prev_total = len(prev_changes) or 1
        cfr = cur_fail / cur_total
        prev_cfr = prev_fail / prev_total
        cfr_window = MetricWindow(
            "change_fail_rate",
            [
                MetricPoint("cfr", cfr, now),
                MetricPoint("cfr", prev_cfr, prev_until),
            ],
        )

        trend = self._compute_trend(
            cur_freq, prev_freq, lead_median, _median(prev_lead_times) if prev_lead_times else 0.0,
            cur_mttr, prev_mttr, cfr, prev_cfr,
            len(cur_changes) > 0 and len(prev_changes) > 0,
        )

        return DORAMetrics(
            deployment_frequency=cur_freq,
            lead_time_median_hours=lead_median,
            lead_time_p95_hours=lead_p95,
            mttr_hours=cur_mttr,
            change_fail_rate=cfr,
            trend=trend,
            windows={
                "deployment_frequency": freq_window,
                "lead_time": lead_window,
                "mttr": mttr_window,
                "change_fail_rate": cfr_window,
            },
        )

    @staticmethod
    def _avg_mttr(incidents: List[dict]) -> float:
        resolved = [i for i in incidents if i.get("mttr_minutes") is not None]
        if not resolved:
            return 0.0
        return sum(i["mttr_minutes"] for i in resolved) / len(resolved) / 60.0

    @staticmethod
    def _compute_trend(
        cur_freq: float, prev_freq: float,
        cur_lt: float, prev_lt: float,
        cur_mttr: float, prev_mttr: float,
        cur_cfr: float, prev_cfr: float,
        has_data: bool = False,
    ) -> TrendDirection:
        if not has_data:
            return TrendDirection.INSUFFICIENT_DATA
        improving = 0
        degrading = 0
        # Deployment frequency: higher is better
        if cur_freq > prev_freq * 1.1:
            improving += 1
        elif cur_freq < prev_freq * 0.9:
            degrading += 1
        # Lead time: lower is better
        if cur_lt < prev_lt * 0.9 and prev_lt > 0:
            improving += 1
        elif cur_lt > prev_lt * 1.1 and prev_lt > 0:
            degrading += 1
        # MTTR: lower is better
        if cur_mttr < prev_mttr * 0.9 and prev_mttr > 0:
            improving += 1
        elif cur_mttr > prev_mttr * 1.1 and prev_mttr > 0:
            degrading += 1
        # Change fail rate: lower is better
        if cur_cfr < prev_cfr * 0.9 and prev_cfr > 0:
            improving += 1
        elif cur_cfr > prev_cfr * 1.1 and prev_cfr > 0:
            degrading += 1

        if improving >= 2:
            return TrendDirection.IMPROVING
        elif degrading >= 2:
            return TrendDirection.DEGRADING
        return TrendDirection.STABLE