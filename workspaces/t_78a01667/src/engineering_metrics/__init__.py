"""Engineering Metrics System — DORA, Flow & Team Health Dashboard.

Provides collectors for DORA metrics (deployment frequency, lead time,
MTTR, change fail rate), flow metrics (cycle time, WIP, throughput),
and a team health survey framework with quarterly pulse surveys.

Usage::

    from engineering_metrics import MetricsEngine

    engine = MetricsEngine(db_path="metrics.db")
    engine.record_deployment(repo="api", env="prod", timestamp=...)
    engine.record_change(repo="api", lead_time_hours=4.5, failed=False)

    dora = engine.dora_metrics(weeks=4)
    flow = engine.flow_metrics(days=30)
    health = engine.team_health_summary()

    print(engine.dashboard().render())
"""
from __future__ import annotations

from .dashboard import Dashboard
from .dora import DORAMetrics, DeploymentRecord, ChangeRecord
from .flow import FlowMetrics, CycleTimeRecord, WorkItem
from .models import (
    MetricPoint,
    MetricWindow,
    TrendDirection,
    AccessLevel,
    TeamHealthScore,
    PulseSurvey,
)
from .storage import MetricsStorage
from .team_health import TeamHealthFramework
from .engine import MetricsEngine

__all__ = [
    "MetricsEngine",
    "Dashboard",
    "DORAMetrics",
    "DeploymentRecord",
    "ChangeRecord",
    "FlowMetrics",
    "CycleTimeRecord",
    "WorkItem",
    "TeamHealthFramework",
    "SurveyResponse",
    "TeamHealthScore",
    "PulseSurvey",
    "MetricPoint",
    "MetricWindow",
    "TrendDirection",
    "AccessLevel",
    "MetricsStorage",
]