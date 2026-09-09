"""Console dashboard renderer for engineering metrics."""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .dora import DORAMetrics
from .flow import FlowMetrics
from .models import TeamHealthScore, TrendDirection
from .team_health import TeamHealthFramework


class Dashboard:
    """ASCII console dashboard for engineering metrics."""

    def __init__(
        self,
        width: int = 72,
        dora: Optional[DORAMetrics] = None,
        flow: Optional[FlowMetrics] = None,
        health: Optional[TeamHealthScore] = None,
        health_framework: Optional[TeamHealthFramework] = None,
    ) -> None:
        self.width = width
        self._dora = dora
        self._flow = flow
        self._health = health
        self._health_framework = health_framework

    def render(self) -> str:
        """Render the full dashboard."""
        parts: List[str] = []
        sep = "=" * self.width

        parts.append(sep)
        parts.append(self._center("ENGINEERING METRICS DASHBOARD"))
        parts.append(self._center(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}"))
        parts.append(sep)
        parts.append("")

        # DORA
        parts.append("--- DORA METRICS ---")
        if self._dora:
            parts.extend(self._render_dora(self._dora))
        else:
            parts.append("  No DORA data available.")
        parts.append("")

        # Flow
        parts.append("--- FLOW METRICS ---")
        if self._flow:
            parts.extend(self._render_flow(self._flow))
        else:
            parts.append("  No flow data available.")
        parts.append("")

        # Team Health
        parts.append("--- TEAM HEALTH ---")
        if self._health:
            parts.extend(self._render_health(self._health))
        else:
            parts.append("  No health survey data available.")
        parts.append("")

        # Insights
        if self._health_framework and self._health:
            parts.append("--- ACTIONABLE INSIGHTS ---")
            insights = self._health_framework.generate_insights(self._health)
            if insights:
                for i, ins in enumerate(insights[:5], 1):
                    parts.append(f"  {i}. [{ins['severity'].upper()}] {ins['action']}")
            else:
                parts.append("  No critical issues detected.")
            parts.append("")

        # Access note
        parts.append(sep)
        parts.append(self._center("Access: read-only | analyst | admin"))
        parts.append(sep)

        return "\n".join(parts)

    def _render_dora(self, d: DORAMetrics) -> List[str]:
        lines = []
        lines.append(f"  Deployment Freq  : {d.deployment_frequency:.2f}/week")
        lines.append(f"  Lead Time Median : {d.lead_time_median_hours:.1f}h")
        lines.append(f"  Lead Time P95    : {d.lead_time_p95_hours:.1f}h")
        lines.append(f"  MTTR             : {d.mttr_hours:.1f}h")
        lines.append(f"  Change Fail Rate : {d.change_fail_rate:.1%}")
        lines.append(f"  Trend            : {d.trend.value}")
        for name, win in d.windows.items():
            trend = win.trend().value
            avg = win.average()
            lines.append(f"    [{name}] avg={avg:.4f} trend={trend}")
        return lines

    def _render_flow(self, f: FlowMetrics) -> List[str]:
        lines = []
        lines.append(f"  Cycle Time Median: {f.cycle_time_median_hours:.1f}h")
        lines.append(f"  Cycle Time P95   : {f.cycle_time_p95_hours:.1f}h")
        lines.append(f"  Avg WIP          : {f.avg_wip:.1f}")
        lines.append(f"  Throughput/week  : {f.throughput_per_week:.1f}")
        lines.append(f"  CT Trend         : {f.cycle_time_trend.value}")
        lines.append(f"  WIP Trend        : {f.wip_trend.value}")
        for name, win in f.windows.items():
            trend = win.trend().value
            avg = win.average()
            lines.append(f"    [{name}] avg={avg:.4f} trend={trend}")
        return lines

    def _render_health(self, h: TeamHealthScore) -> List[str]:
        lines = []
        bar = self._bar(h.overall_score / 100.0, width=30)
        lines.append(f"  Overall Score    : {h.overall_score:.1f}/100 [{bar}]")
        lines.append(f"  Surveys          : {h.survey_count}")
        for dim, val in h.dimensions.items():
            trend = h.trends.get(dim, TrendDirection.INSUFFICIENT_DATA)
            bar = self._bar(val / 100.0, width=20)
            lines.append(f"    {dim:<15} {val:5.1f} [{bar}] {trend.value}")
        return lines

    @staticmethod
    def _bar(fraction: float, width: int = 20) -> str:
        fraction = max(0.0, min(1.0, fraction))
        filled = int(round(fraction * width))
        return "#" * filled + "-" * (width - filled)

    @staticmethod
    def _center(text: str) -> str:
        return text.center(72)