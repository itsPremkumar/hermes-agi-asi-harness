"""Engineering metrics system tests."""
import sys
import time
from pathlib import Path

import pytest

# Ensure src/ is on sys.path
src = Path(__file__).resolve().parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from engineering_metrics import (
    MetricsEngine,
    DORAMetrics,
    FlowMetrics,
    TeamHealthScore,
    PulseSurvey,
    TrendDirection,
    DeploymentRecord,
    ChangeRecord,
)
from engineering_metrics.storage import MetricsStorage
from engineering_metrics.dora import DORACompute, DeploymentRecord as DR, ChangeRecord as CR
from engineering_metrics.flow import FlowCompute, CycleTimeRecord, WorkItem
from engineering_metrics.team_health import TeamHealthFramework
from engineering_metrics.dashboard import Dashboard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine(tmp_path):
    db = tmp_path / "metrics.db"
    return MetricsEngine(db_path=str(db), access_level="analyst")


@pytest.fixture
def storage(tmp_path):
    db = tmp_path / "metrics.db"
    return MetricsStorage(str(db))


# ---------------------------------------------------------------------------
# DORA Compute
# ---------------------------------------------------------------------------

class TestDORACompute:
    def test_empty_dora(self, storage):
        compute = DORACompute(storage)
        metrics = compute.compute(weeks=4)
        assert metrics.deployment_frequency == 0.0
        assert metrics.lead_time_median_hours == 0.0
        assert metrics.mttr_hours == 0.0
        assert metrics.change_fail_rate == 0.0
        assert metrics.trend == TrendDirection.INSUFFICIENT_DATA

    def test_deployment_frequency(self, storage):
        now = time.time()
        for i in range(8):
            storage.insert_deployment("api", "prod", now - i * 86400)
        compute = DORACompute(storage)
        metrics = compute.compute(weeks=4)
        assert metrics.deployment_frequency == 2.0  # 8 / 4 weeks

    def test_lead_time(self, storage):
        now = time.time()
        storage.insert_change("api", lead_time_hours=2.0, failed=False, timestamp=now - 86400)
        storage.insert_change("api", lead_time_hours=4.0, failed=False, timestamp=now - 86400)
        storage.insert_change("api", lead_time_hours=10.0, failed=True, timestamp=now - 86400)
        compute = DORACompute(storage)
        metrics = compute.compute(weeks=4)
        assert metrics.lead_time_median_hours == 4.0
        assert metrics.change_fail_rate == pytest.approx(1 / 3)

    def test_mttr(self, storage):
        now = time.time()
        inc_id = storage.insert_incident("outage", started_at=now - 7200)
        storage.resolve_incident(inc_id, resolved_at=now - 3600)
        compute = DORACompute(storage)
        metrics = compute.compute(weeks=4)
        assert metrics.mttr_hours == pytest.approx(1.0)  # 60 min / 60

    def test_trend_improving(self, storage):
        now = time.time()
        # Old changes (worse lead times, more failures) — in prev window
        for i in range(4):
            storage.insert_change("api", lead_time_hours=10.0, failed=True, timestamp=now - 35 * 86400 - i * 86400)
        # Recent changes (better lead times, fewer failures) — in cur window
        for i in range(8):
            storage.insert_change("api", lead_time_hours=2.0, failed=False, timestamp=now - i * 86400)
        compute = DORACompute(storage)
        metrics = compute.compute(weeks=4, prev_weeks=4)
        assert metrics.trend == TrendDirection.IMPROVING


# ---------------------------------------------------------------------------
# Flow Compute
# ---------------------------------------------------------------------------

class TestFlowCompute:
    def test_empty_flow(self, storage):
        compute = FlowCompute(storage)
        metrics = compute.compute(days=30)
        assert metrics.cycle_time_median_hours == 0.0
        assert metrics.throughput_per_week == 0.0
        assert metrics.trend == TrendDirection.INSUFFICIENT_DATA

    def test_cycle_time(self, storage):
        now = time.time()
        for i, ct in enumerate([2.0, 4.0, 6.0, 8.0, 10.0]):
            storage.insert_cycle_time(f"WI-{i}", ct, timestamp=now - i * 86400)
        compute = FlowCompute(storage)
        metrics = compute.compute(days=30)
        assert metrics.cycle_time_median_hours == 6.0
        assert metrics.throughput_per_week > 0

    def test_cycle_time_p95(self, storage):
        now = time.time()
        for i in range(20):
            storage.insert_cycle_time(f"WI-{i}", float(i + 1), timestamp=now - i * 86400)
        compute = FlowCompute(storage)
        metrics = compute.compute(days=30)
        assert metrics.cycle_time_p95_hours > metrics.cycle_time_median_hours


# ---------------------------------------------------------------------------
# Engine integration
# ---------------------------------------------------------------------------

class TestMetricsEngine:
    def test_record_and_compute(self, engine):
        now = time.time()
        engine.record_deployment("api", "prod", timestamp=now)
        engine.record_change("api", lead_time_hours=3.0, failed=False)
        engine.record_change("api", lead_time_hours=8.0, failed=True)
        engine.record_incident("outage", started_at=now - 3600, severity="high")
        engine.resolve_incident(1, resolved_at=now - 1800)
        engine.record_cycle_time("WI-1", 5.0)
        engine.record_pulse_survey("s1", "alice", {"satisfaction": 4, "autonomy": 3})

        dora = engine.dora_metrics(weeks=4)
        assert dora.deployment_frequency == 1.0 / 4  # 1 deployment / 4 weeks
        assert dora.change_fail_rate == 0.5
        assert dora.mttr_hours == pytest.approx(0.5)  # 30 min

        flow = engine.flow_metrics(days=30)
        assert flow.cycle_time_median_hours == 5.0

        health = engine.team_health_summary()
        assert health.survey_count == 1
        assert "satisfaction" in health.dimensions

    def test_dashboard_render(self, engine):
        now = time.time()
        engine.record_deployment("api", "prod", timestamp=now)
        engine.record_change("api", lead_time_hours=3.0, failed=False)
        output = engine.dashboard().render()
        assert "ENGINEERING METRICS DASHBOARD" in output
        assert "DORA METRICS" in output
        assert "FLOW METRICS" in output
        assert "TEAM HEALTH" in output

    def test_access_level(self, engine):
        assert engine.access_level == "analyst"
        engine.set_access_level("admin")
        assert engine.access_level == "admin"
        with pytest.raises(ValueError):
            engine.set_access_level("invalid")

    def test_record_survey_dimensions(self, engine):
        engine.record_pulse_survey("s1", "bob", {"satisfaction": 5, "collaboration": 4, "wellbeing": 3})
        health = engine.team_health_summary()
        assert health.dimensions["satisfaction"] > 0
        assert health.dimensions["wellbeing"] > 0


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class TestStorage:
    def test_deployments(self, storage):
        now = time.time()
        id1 = storage.insert_deployment("api", "prod", now, {"tag": "v1.0"})
        id2 = storage.insert_deployment("api", "staging", now - 100)
        rows = storage.get_deployments(now - 200)
        assert len(rows) == 2
        prod_rows = storage.get_deployments(now - 200, env="prod")
        assert len(prod_rows) == 1

    def test_changes(self, storage):
        now = time.time()
        storage.insert_change("api", 2.5, failed=False, PR_number=42, timestamp=now - 100)
        storage.insert_change("api", 5.0, failed=True, PR_number=43, timestamp=now - 50)
        rows = storage.get_changes(now - 200)
        assert len(rows) == 2
        # Most recent first (43 is newer)
        assert rows[0]["PR_number"] == 43

    def test_incidents(self, storage):
        now = time.time()
        inc_id = storage.insert_incident("db-down", started_at=now - 3600, severity="critical")
        storage.resolve_incident(inc_id, resolved_at=now - 1800)
        rows = storage.get_incidents(now - 7200)
        assert len(rows) == 1
        assert rows[0]["mttr_minutes"] == pytest.approx(30.0)

    def test_cycle_times(self, storage):
        now = time.time()
        storage.insert_cycle_time("WI-1", 3.5, wip_at_start=2)
        rows = storage.get_cycle_times(now - 100)
        assert len(rows) == 1
        assert rows[0]["cycle_time_hours"] == 3.5

    def test_pulse_surveys(self, storage):
        now = time.time()
        from engineering_metrics.models import PulseSurvey
        s = PulseSurvey("sid1", "alice", timestamp=now, scores={"satisfaction": 4})
        storage.insert_pulse_survey(s)
        rows = storage.get_pulse_surveys(now - 100)
        assert len(rows) == 1

    def test_config(self, storage):
        storage.set_config("theme", "dark")
        assert storage.get_config("theme") == "dark"
        assert storage.get_config("missing", "default") == "default"