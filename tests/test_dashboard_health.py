"""Tests for HealthMonitor."""
from core.dashboard.health import HealthMonitor, HealthStatus


class TestHealthMonitor:
    def test_create(self):
        hm = HealthMonitor()
        assert hm.component_count() == 0

    def test_update(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY, 5.0, "OK")
        assert hm.component_count() == 1

    def test_get(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY)
        check = hm.get("api")
        assert check is not None
        assert check.status == HealthStatus.HEALTHY

    def test_get_all(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY)
        hm.update("db", HealthStatus.DEGRADED)
        all_checks = hm.get_all()
        assert len(all_checks) == 2

    def test_overall_status_healthy(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY)
        assert hm.overall_status() == HealthStatus.HEALTHY

    def test_overall_status_degraded(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY)
        hm.update("db", HealthStatus.DEGRADED)
        assert hm.overall_status() == HealthStatus.DEGRADED

    def test_overall_status_unhealthy(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY)
        hm.update("db", HealthStatus.UNHEALTHY)
        assert hm.overall_status() == HealthStatus.UNHEALTHY

    def test_overall_status_unknown(self):
        hm = HealthMonitor()
        assert hm.overall_status() == HealthStatus.UNKNOWN

    def test_healthy_count(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY)
        hm.update("db", HealthStatus.DEGRADED)
        assert hm.healthy_count() == 1

    def test_get_history(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY)
        hm.update("api", HealthStatus.DEGRADED)
        history = hm.get_history("api")
        assert len(history) == 2

    def test_get_state(self):
        hm = HealthMonitor()
        hm.update("api", HealthStatus.HEALTHY)
        state = hm.get_state()
        assert state["overall"] == "healthy"
        assert state["components"] == 1
        assert state["healthy"] == 1
