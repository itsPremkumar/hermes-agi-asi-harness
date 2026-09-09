"""Metrics engine — orchestrates DORA, flow, and team health computations."""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .dora import DORACompute, DeploymentRecord, ChangeRecord, DORAMetrics
from .flow import FlowCompute, CycleTimeRecord, FlowMetrics, WorkItem
from .models import AccessLevel, MetricPoint, MetricWindow, TrendDirection
from .storage import MetricsStorage
from .team_health import TeamHealthFramework, TeamHealthScore, PulseSurvey
from .dashboard import Dashboard


class MetricsEngine:
    """Top-level engine for engineering metrics collection and dashboarding.

    Parameters
    ----------
    db_path
        Path to the SQLite metrics database.
    access_level
        Access level controlling what data operations are permitted.
    """

    def __init__(self, db_path: str = ":memory:", access_level: str = "read_only") -> None:
        self._storage = MetricsStorage(db_path)
        self._access_level = access_level
        self._dora = DORACompute(self._storage)
        self._flow = FlowCompute(self._storage)
        self._health = TeamHealthFramework(self._storage)

    # --- DORA ---

    def record_deployment(
        self, repo: str, env: str = "prod", timestamp: Optional[float] = None, **metadata
    ) -> int:
        """Record a deployment event."""
        ts = timestamp or time.time()
        return self._storage.insert_deployment(repo, env, ts, metadata)

    def record_change(
        self, repo: str, lead_time_hours: float, failed: bool = False, PR_number: Optional[int] = None, **metadata
    ) -> int:
        """Record a code change / PR."""
        return self._storage.insert_change(repo, lead_time_hours, failed, PR_number, metadata=metadata)

    def record_incident(
        self, title: str, started_at: float, severity: str = "medium", **metadata
    ) -> int:
        """Record an incident."""
        return self._storage.insert_incident(title, started_at, severity, metadata)

    def resolve_incident(self, incident_id: int, resolved_at: float) -> None:
        """Resolve an incident and compute MTTR."""
        self._storage.resolve_incident(incident_id, resolved_at)

    def record_cycle_time(
        self, work_item_id: str, cycle_time_hours: float, repo: str = "", wip_at_start: int = 0, timestamp: Optional[float] = None, **metadata
    ) -> int:
        """Record a cycle time measurement."""
        return self._storage.insert_cycle_time(work_item_id, cycle_time_hours, repo, wip_at_start, timestamp=timestamp, metadata=metadata)

    def record_pulse_survey(
        self, survey_id: str, respondent: str, scores: Dict[str, float], comments: str = "", period: str = "current"
    ) -> int:
        """Record a pulse survey response."""
        survey = PulseSurvey(
            survey_id=survey_id, respondent=respondent, scores=scores, comments=comments, period=period
        )
        return self._storage.insert_pulse_survey(survey)

    # --- Computations ---

    def dora_metrics(self, weeks: int = 4, prev_weeks: int = 4) -> DORAMetrics:
        """Compute DORA metrics over the last *weeks*."""
        return self._dora.compute(weeks, prev_weeks)

    def flow_metrics(self, days: int = 30, prev_days: int = 30) -> FlowMetrics:
        """Compute flow metrics over the last *days*."""
        return self._flow.compute(days, prev_days)

    def team_health_summary(self, since: Optional[float] = None, period: Optional[str] = None) -> TeamHealthScore:
        """Compute team health summary."""
        return self._health.get_summary(since=since, period=period)

    # --- Dashboard ---

    def dashboard(self) -> Dashboard:
        """Build a rendered dashboard from current data."""
        dora = self._dora.compute()
        flow = self._flow.compute()
        health = self._health.get_summary()
        return Dashboard(dora=dora, flow=flow, health=health, health_framework=self._health)

    # --- Access ---

    @property
    def access_level(self) -> str:
        return self._access_level

    def set_access_level(self, level: str) -> None:
        if level not in ("read_only", "analyst", "admin"):
            raise ValueError(f"Invalid access level: {level!r}")
        self._access_level = level

    # --- Storage ---

    @property
    def storage(self) -> MetricsStorage:
        return self._storage