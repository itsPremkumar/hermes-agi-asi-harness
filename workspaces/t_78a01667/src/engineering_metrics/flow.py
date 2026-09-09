"""Flow metrics: cycle time, WIP, throughput."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import MetricPoint, MetricWindow, TrendDirection
from .storage import MetricsStorage


@dataclass
class WorkItem:
    """A tracked work item."""

    work_item_id: str
    repo: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    done_at: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class CycleTimeRecord:
    """A cycle time measurement for a work item."""

    work_item_id: str
    cycle_time_hours: float
    repo: str = ""
    wip_at_start: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class FlowMetrics:
    """Computed flow metrics."""

    cycle_time_median_hours: float
    cycle_time_p95_hours: float
    avg_wip: float
    throughput_per_week: float
    cycle_time_trend: TrendDirection = TrendDirection.STABLE
    wip_trend: TrendDirection = TrendDirection.STABLE
    trend: TrendDirection = TrendDirection.STABLE
    windows: Dict[str, MetricWindow] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "cycle_time_median_hours": round(self.cycle_time_median_hours, 2),
            "cycle_time_p95_hours": round(self.cycle_time_p95_hours, 2),
            "avg_wip": round(self.avg_wip, 2),
            "throughput_per_week": round(self.throughput_per_week, 2),
            "cycle_time_trend": self.cycle_time_trend.value,
            "wip_trend": self.wip_trend.value,
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


class FlowCompute:
    """Compute flow metrics from storage."""

    def __init__(self, storage: MetricsStorage) -> None:
        self._storage = storage

    def compute(self, days: int = 30, prev_days: int = 30) -> FlowMetrics:
        now = time.time()
        day_sec = 86400

        cur_since = now - days * day_sec
        prev_since = cur_since - prev_days * day_sec

        cur_records = self._storage.get_cycle_times(cur_since)
        prev_records = self._storage.get_cycle_times(prev_since)

        cur_cycles = [r["cycle_time_hours"] for r in cur_records if r.get("cycle_time_hours", 0) > 0]
        prev_cycles = [r["cycle_time_hours"] for r in prev_records if r.get("cycle_time_hours", 0) > 0]

        # Cycle time
        ct_median = _median(cur_cycles)
        ct_p95 = _percentile(cur_cycles, 95) if cur_cycles else 0.0
        ct_window = MetricWindow(
            "cycle_time_hours",
            [
                MetricPoint("ct", ct_median, now),
                MetricPoint("ct", _median(prev_cycles), prev_since),
            ],
        )

        # WIP: approximate from in-flight items
        cur_wip = len([r for r in cur_records if r.get("wip_at_start", 0) > 0])
        prev_wip = len([r for r in prev_records if r.get("wip_at_start", 0) > 0])
        wip_window = MetricWindow(
            "wip",
            [
                MetricPoint("wip", float(cur_wip), now),
                MetricPoint("wip", float(prev_wip), prev_since),
            ],
        )

        # Throughput: completed items per week
        completed = len(cur_records)
        throughput = completed / (days / 7) if days else 0.0
        prev_completed = len(prev_records)
        prev_throughput = prev_completed / (prev_days / 7) if prev_days else 0.0
        tp_window = MetricWindow(
            "throughput",
            [
                MetricPoint("tp", throughput, now),
                MetricPoint("tp", prev_throughput, prev_since),
            ],
        )

        ct_trend = self._classify_trend(ct_median, _median(prev_cycles) if prev_cycles else 0.0, lower_is_better=True)
        wip_trend = self._classify_trend(float(cur_wip), float(prev_wip), lower_is_better=True)

        return FlowMetrics(
            cycle_time_median_hours=ct_median,
            cycle_time_p95_hours=ct_p95,
            avg_wip=float(cur_wip) if cur_wip else 0.0,
            throughput_per_week=throughput,
            cycle_time_trend=ct_trend,
            wip_trend=wip_trend,
            trend=ct_trend,
            windows={
                "cycle_time": ct_window,
                "wip": wip_window,
                "throughput": tp_window,
            },
        )

    @staticmethod
    def _classify_trend(
        cur: float, prev: float, lower_is_better: bool = True
    ) -> TrendDirection:
        if prev == 0:
            return TrendDirection.INSUFFICIENT_DATA
        if lower_is_better:
            if cur < prev * 0.9:
                return TrendDirection.IMPROVING
            elif cur > prev * 1.1:
                return TrendDirection.DEGRADING
        else:
            if cur > prev * 1.1:
                return TrendDirection.IMPROVING
            elif cur < prev * 0.9:
                return TrendDirection.DEGRADING
        return TrendDirection.STABLE