"""Tests for dynamic config, high availability, and Hermes integration."""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness.core.dynamic_config import DynamicConfig
from harness.core.hermes_integration import (
    CronJob,
    HermesAgentIntegration,
    KanbanCard,
    MCPEndpoint,
    ProfileConfig,
)
from harness.core.high_availability import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    FailoverManager,
    GracefulDegradation,
)

# ============== Dynamic Config Tests ==============

class TestDynamicConfig:
    def test_create(self):
        config = DynamicConfig()
        assert config.get_all() == {}

    def test_get_set(self):
        config = DynamicConfig()
        config.set("key", "value")
        assert config.get("key") == "value"

    def test_get_default(self):
        config = DynamicConfig()
        assert config.get("nonexistent", "default") == "default"

    def test_get_all(self):
        config = DynamicConfig()
        config.set("a", 1)
        config.set("b", 2)
        assert config.get_all() == {"a": 1, "b": 2}

    def test_save_and_load(self, tmp_path):
        config = DynamicConfig(config_path=str(tmp_path / "config.json"))
        config.set("key", "value")
        config.save()

        config2 = DynamicConfig(config_path=str(tmp_path / "config.json"))
        config2.load()
        assert config2.get("key") == "value"

    def test_change_listener(self):
        config = DynamicConfig()
        changes = []
        config.add_listener(lambda e: changes.append(e))
        config.set("key", "value")
        assert len(changes) == 1
        assert changes[0].key == "key"

    def test_remove_listener(self):
        config = DynamicConfig()

        def listener(e):
            return None

        config.add_listener(listener)
        assert config.remove_listener(listener) is True

    def test_change_log(self):
        config = DynamicConfig()
        config.set("a", 1)
        config.set("a", 2)
        log = config.get_change_log()
        assert len(log) == 2

    def test_clear_log(self):
        config = DynamicConfig()
        config.set("a", 1)
        config.clear_log()
        assert len(config.get_change_log()) == 0

    def test_hot_reload(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        config = DynamicConfig(config_path=config_path, reload_interval=0.5)
        config.save()
        config.start()
        time.sleep(0.1)

        # Modify file externally
        import json
        with open(config_path, "w") as f:
            json.dump({"reloaded": True}, f)

        time.sleep(1.0)  # Wait for reload
        config.stop()
        assert config.get("reloaded") is True


# ============== Circuit Breaker Tests ==============

class TestCircuitBreaker:
    def test_create(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_can_execute_closed(self):
        cb = CircuitBreaker("test")
        assert cb.can_execute() is True

    def test_record_failure(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        cb.record_failure()
        assert cb._failure_count == 1

    def test_open_after_threshold(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=2))
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_cannot_execute_open(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))
        cb.record_failure()
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1))
        cb.record_failure()
        time.sleep(0.2)
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_close_after_successes(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=2))
        cb.record_failure()
        time.sleep(0.2)
        cb.can_execute()  # Enter half-open
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopen_on_half_open_failure(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=3))
        cb.record_failure()
        time.sleep(0.2)
        cb.can_execute()  # Enter half-open
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_get_status(self):
        cb = CircuitBreaker("test")
        status = cb.get_status()
        assert "name" in status
        assert "state" in status


# ============== Failover Manager Tests ==============

class TestFailoverManager:
    def test_create(self):
        fm = FailoverManager()
        assert fm.get_status()["total_primaries"] == 0

    def test_register(self):
        fm = FailoverManager()
        fm.register("p1", "primary_obj", "backup_obj")
        assert fm.get_status()["total_primaries"] == 1

    def test_get_active_primary(self):
        fm = FailoverManager()
        fm.register("p1", "primary", "backup")
        assert fm.get_active("p1") == "primary"

    def test_failover(self):
        fm = FailoverManager()
        fm.register("p1", "primary", "backup")
        assert fm.failover("p1") is True
        assert fm.get_active("p1") == "backup"

    def test_failover_no_backup(self):
        fm = FailoverManager()
        fm.register("p1", "primary", None)
        assert fm.failover("p1") is False

    def test_restore_primary(self):
        fm = FailoverManager()
        fm.register("p1", "primary", "backup")
        fm.failover("p1")
        assert fm.restore_primary("p1") is True
        assert fm.get_active("p1") == "primary"

    def test_get_failover_count(self):
        fm = FailoverManager()
        fm.register("p1", "primary", "backup")
        fm.failover("p1")
        fm.restore_primary("p1")
        fm.failover("p1")
        assert fm.get_failover_count("p1") == 2


# ============== Graceful Degradation Tests ==============

class TestGracefulDegradation:
    def test_create(self):
        gd = GracefulDegradation()
        assert gd.get_status()["total_degraded"] == 0

    def test_degrade(self):
        gd = GracefulDegradation()
        gd.degrade("p1", level=2)
        assert gd.get_degradation_level("p1") == 2

    def test_restore(self):
        gd = GracefulDegradation()
        gd.degrade("p1")
        gd.restore("p1")
        assert gd.get_degradation_level("p1") == 0

    def test_disable_enable(self):
        gd = GracefulDegradation()
        gd.disable("p1")
        assert gd.is_available("p1") is False
        gd.enable("p1")
        assert gd.is_available("p1") is True

    def test_register_fallback(self):
        gd = GracefulDegradation()
        gd.register_fallback("p1", "fallback_obj")
        assert gd.get_fallback("p1") == "fallback_obj"


# ============== Hermes Integration Tests ==============

class TestHermesAgentIntegration:
    def test_create(self):
        integration = HermesAgentIntegration()
        assert integration.get_status()["profiles"] == 0

    def test_create_profile(self):
        integration = HermesAgentIntegration()
        profile = ProfileConfig(name="default", plugins=["p1", "p2"])
        integration.create_profile(profile)
        assert integration.get_status()["profiles"] == 1

    def test_get_profile(self):
        integration = HermesAgentIntegration()
        profile = ProfileConfig(name="test", plugins=[])
        integration.create_profile(profile)
        retrieved = integration.get_profile("test")
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_update_profile(self):
        integration = HermesAgentIntegration()
        integration.create_profile(ProfileConfig(name="test", enabled=True))
        assert integration.update_profile("test", enabled=False) is True
        assert integration.get_profile("test").enabled is False

    def test_delete_profile(self):
        integration = HermesAgentIntegration()
        integration.create_profile(ProfileConfig(name="test"))
        assert integration.delete_profile("test") is True
        assert integration.get_status()["profiles"] == 0

    def test_list_enabled_profiles(self):
        integration = HermesAgentIntegration()
        integration.create_profile(ProfileConfig(name="p1", enabled=True))
        integration.create_profile(ProfileConfig(name="p2", enabled=False))
        enabled = integration.list_enabled_profiles()
        assert len(enabled) == 1

    def test_create_card(self):
        integration = HermesAgentIntegration()
        card = KanbanCard(id="c1", title="Task 1")
        integration.create_card(card)
        assert integration.get_status()["kanban_cards"] == 1

    def test_move_card(self):
        integration = HermesAgentIntegration()
        integration.create_card(KanbanCard(id="c1", title="Task"))
        assert integration.move_card("c1", "in_progress") is True
        assert integration.get_card("c1").status == "in_progress"

    def test_list_cards_by_status(self):
        integration = HermesAgentIntegration()
        integration.create_card(KanbanCard(id="c1", title="T1", status="todo"))
        integration.create_card(KanbanCard(id="c2", title="T2", status="done"))
        todo = integration.list_cards(status="todo")
        assert len(todo) == 1

    def test_add_cron_job(self):
        integration = HermesAgentIntegration()
        job = CronJob(id="j1", plugin_id="p1", action="run")
        integration.add_cron_job(job)
        assert integration.get_status()["cron_jobs"] == 1

    def test_enable_disable_cron(self):
        integration = HermesAgentIntegration()
        integration.add_cron_job(CronJob(id="j1", plugin_id="p1", action="run"))
        integration.disable_cron_job("j1")
        assert integration.get_cron_job("j1").enabled is False
        integration.enable_cron_job("j1")
        assert integration.get_cron_job("j1").enabled is True

    def test_register_endpoint(self):
        integration = HermesAgentIntegration()
        endpoint = MCPEndpoint(id="e1", plugin_id="p1", transport="stdio")
        integration.register_endpoint(endpoint)
        assert integration.get_status()["mcp_endpoints"] == 1

    def test_list_endpoints_by_transport(self):
        integration = HermesAgentIntegration()
        integration.register_endpoint(MCPEndpoint(id="e1", plugin_id="p1", transport="stdio"))
        integration.register_endpoint(MCPEndpoint(id="e2", plugin_id="p2", transport="http"))
        stdio = integration.list_endpoints(transport="stdio")
        assert len(stdio) == 1

    def test_get_status(self):
        integration = HermesAgentIntegration()
        integration.create_profile(ProfileConfig(name="test"))
        integration.create_card(KanbanCard(id="c1", title="T"))
        status = integration.get_status()
        assert "profiles" in status
        assert "kanban_cards" in status
