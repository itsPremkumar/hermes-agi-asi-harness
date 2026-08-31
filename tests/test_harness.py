"""Tests for hermes-agi-asi-harness plugin framework."""

from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness.plugin_base import Plugin, PluginMetadata, PluginStatus
from harness.registry import PluginRegistry
from harness.lifecycle import LifecycleManager, LifecycleEvent, LifecycleHook
from harness.dependency_resolver import DependencyGraph, DependencyResolver
from harness.config import PluginConfig, ConfigValidator
from harness.health import HealthMonitor, HealthStatus, HealthCheckResult
from harness.versioning import Version, VersionRange, Compatibility


# ==================== Plugin Base Tests ====================

class TestPluginMetadata:
    def test_create_metadata(self):
        meta = PluginMetadata(id="test", name="Test Plugin", version="1.0.0")
        assert meta.id == "test"
        assert meta.name == "Test Plugin"
        assert meta.version == "1.0.0"
        assert meta.dependencies == []

    def test_provides_defaults_to_id(self):
        meta = PluginMetadata(id="test", name="Test")
        assert meta.provides == ["test"]

    def test_provides_can_be_overridden(self):
        meta = PluginMetadata(id="test", name="Test", provides=["cap1", "cap2"])
        assert meta.provides == ["cap1", "cap2"]


class TestPluginStatus:
    def test_status_values(self):
        assert PluginStatus.REGISTERED.value == "registered"
        assert PluginStatus.ACTIVE.value == "active"
        assert PluginStatus.ERROR.value == "error"


class TestPlugin:
    def test_create_plugin(self):
        meta = PluginMetadata(id="test", name="Test Plugin")
        plugin = Plugin(meta)
        assert plugin.id == "test"
        assert plugin.status == PluginStatus.REGISTERED

    def test_is_active(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        assert plugin.is_active is False

    def test_has_error(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        assert plugin.has_error is False

    def test_get_status(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        assert plugin.get_status() == PluginStatus.REGISTERED

    def test_set_status(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.set_status(PluginStatus.ACTIVE)
        assert plugin.status == PluginStatus.ACTIVE

    def test_set_config(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.set_config({"key": "value"})
        assert plugin.get_config() == {"key": "value"}

    def test_record_error(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.record_error("Something went wrong")
        assert plugin.has_error
        assert plugin.get_error() == "Something went wrong"

    def test_clear_error(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.record_error("Error")
        plugin.clear_error()
        assert plugin.get_error() is None

    def test_get_error_count(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.record_error("Error 1")
        plugin.record_error("Error 2")
        assert plugin.get_error_count() == 2

    def test_on_load(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.on_load()
        assert plugin.status == PluginStatus.LOADED

    def test_on_init(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.on_load()
        plugin.on_init()
        assert plugin.status == PluginStatus.ACTIVE

    def test_on_pause(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.on_load()
        plugin.on_init()
        plugin.on_pause()
        assert plugin.status == PluginStatus.PAUSED

    def test_on_resume(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.on_load()
        plugin.on_init()
        plugin.on_pause()
        plugin.on_resume()
        assert plugin.status == PluginStatus.ACTIVE

    def test_on_stop(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        plugin.on_load()
        plugin.on_init()
        plugin.on_stop()
        assert plugin.status == PluginStatus.STOPPED

    def test_health_check_default(self):
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        result = plugin.health_check()
        assert result["healthy"] is True

    def test_get_info(self):
        meta = PluginMetadata(id="test", name="Test", version="1.0.0")
        plugin = Plugin(meta)
        info = plugin.get_info()
        assert info["id"] == "test"
        assert info["name"] == "Test"
        assert info["version"] == "1.0.0"
        assert info["status"] == "registered"


# ==================== Plugin Registry Tests ====================

class TestPluginRegistry:
    def test_register_plugin(self):
        reg = PluginRegistry()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        key = reg.register(plugin)
        assert key is not None
        assert reg.count() == 1

    def test_register_duplicate_id(self):
        reg = PluginRegistry()
        meta = PluginMetadata(id="test", name="Test")
        reg.register(Plugin(meta))
        with pytest.raises(ValueError):
            reg.register(Plugin(meta))

    def test_register_duplicate_name(self):
        reg = PluginRegistry()
        reg.register(Plugin(PluginMetadata(id="test1", name="SameName")))
        with pytest.raises(ValueError):
            reg.register(Plugin(PluginMetadata(id="test2", name="SameName")))

    def test_unregister_plugin(self):
        reg = PluginRegistry()
        meta = PluginMetadata(id="test", name="Test")
        reg.register(Plugin(meta))
        assert reg.unregister("test") is True
        assert reg.count() == 0

    def test_unregister_not_found(self):
        reg = PluginRegistry()
        assert reg.unregister("nonexistent") is False

    def test_get_plugin(self):
        reg = PluginRegistry()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        reg.register(plugin)
        retrieved = reg.get("test")
        assert retrieved is plugin

    def test_get_by_name(self):
        reg = PluginRegistry()
        meta = PluginMetadata(id="test", name="MyPlugin")
        plugin = Plugin(meta)
        reg.register(plugin)
        retrieved = reg.get_by_name("MyPlugin")
        assert retrieved is plugin

    def test_get_all(self):
        reg = PluginRegistry()
        reg.register(Plugin(PluginMetadata(id="t1", name="T1")))
        reg.register(Plugin(PluginMetadata(id="t2", name="T2")))
        assert len(reg.get_all()) == 2

    def test_get_by_tag(self):
        reg = PluginRegistry()
        reg.register(Plugin(PluginMetadata(id="t1", name="T1", tags=["fast"])))
        reg.register(Plugin(PluginMetadata(id="t2", name="T2", tags=["fast", "reliable"])))
        reg.register(Plugin(PluginMetadata(id="t3", name="T3", tags=["slow"])))
        results = reg.get_by_tag("fast")
        assert len(results) == 2

    def test_get_by_capability(self):
        reg = PluginRegistry()
        reg.register(Plugin(PluginMetadata(id="t1", name="T1", provides=["read"])))
        reg.register(Plugin(PluginMetadata(id="t2", name="T2", provides=["read", "write"])))
        reg.register(Plugin(PluginMetadata(id="t3", name="T3", provides=["execute"])))
        results = reg.get_by_capability("read")
        assert len(results) == 2

    def test_get_active(self):
        reg = PluginRegistry()
        p1 = Plugin(PluginMetadata(id="t1", name="T1"))
        p1.set_status(PluginStatus.ACTIVE)
        p2 = Plugin(PluginMetadata(id="t2", name="T2"))
        p2.set_status(PluginStatus.STOPPED)
        reg.register(p1)
        reg.register(p2)
        active = reg.get_active()
        assert len(active) == 1

    def test_get_with_errors(self):
        reg = PluginRegistry()
        p1 = Plugin(PluginMetadata(id="t1", name="T1"))
        p1.record_error("Error")
        p2 = Plugin(PluginMetadata(id="t2", name="T2"))
        reg.register(p1)
        reg.register(p2)
        errors = reg.get_with_errors()
        assert len(errors) == 1

    def test_count_by_status(self):
        reg = PluginRegistry()
        p1 = Plugin(PluginMetadata(id="t1", name="T1"))
        p1.set_status(PluginStatus.ACTIVE)
        p2 = Plugin(PluginMetadata(id="t2", name="T2"))
        p2.set_status(PluginStatus.ACTIVE)
        p3 = Plugin(PluginMetadata(id="t3", name="T3"))
        reg.register(p1)
        reg.register(p2)
        reg.register(p3)
        assert reg.count_by_status(PluginStatus.ACTIVE) == 2

    def test_is_registered(self):
        reg = PluginRegistry()
        reg.register(Plugin(PluginMetadata(id="test", name="Test")))
        assert reg.is_registered("test") is True
        assert reg.is_registered("nonexistent") is False

    def test_is_name_registered(self):
        reg = PluginRegistry()
        reg.register(Plugin(PluginMetadata(id="test", name="MyPlugin")))
        assert reg.is_name_registered("MyPlugin") is True
        assert reg.is_name_registered("Other") is False

    def test_clear(self):
        reg = PluginRegistry()
        reg.register(Plugin(PluginMetadata(id="t1", name="T1")))
        reg.register(Plugin(PluginMetadata(id="t2", name="T2")))
        reg.clear()
        assert reg.count() == 0


# ==================== Lifecycle Manager Tests ====================

class TestLifecycleEvent:
    def test_event_values(self):
        assert LifecycleEvent.BEFORE_LOAD.value == "before_load"
        assert LifecycleEvent.AFTER_STOP.value == "after_stop"


class TestLifecycleManager:
    def test_load(self):
        lc = LifecycleManager()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        lc.load(plugin)
        assert plugin.status == PluginStatus.LOADED

    def test_init(self):
        lc = LifecycleManager()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        lc.load(plugin)
        lc.init(plugin)
        assert plugin.status == PluginStatus.ACTIVE

    def test_start(self):
        lc = LifecycleManager()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        lc.start(plugin)
        assert plugin.status == PluginStatus.ACTIVE

    def test_pause(self):
        lc = LifecycleManager()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        lc.start(plugin)
        lc.pause(plugin)
        assert plugin.status == PluginStatus.PAUSED

    def test_resume(self):
        lc = LifecycleManager()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        lc.start(plugin)
        lc.pause(plugin)
        lc.resume(plugin)
        assert plugin.status == PluginStatus.ACTIVE

    def test_stop(self):
        lc = LifecycleManager()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        lc.start(plugin)
        lc.stop(plugin)
        assert plugin.status == PluginStatus.STOPPED

    def test_restart(self):
        lc = LifecycleManager()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        lc.start(plugin)
        lc.restart(plugin)
        assert plugin.status == PluginStatus.ACTIVE

    def test_add_hook(self):
        lc = LifecycleManager()
        callback = lambda p: None
        hook = LifecycleHook(event=LifecycleEvent.BEFORE_LOAD, callback=callback)
        lc.add_hook(hook)
        assert len(lc._hooks[LifecycleEvent.BEFORE_LOAD]) == 1

    def test_remove_hook(self):
        lc = LifecycleManager()
        callback = lambda p: None
        hook = LifecycleHook(event=LifecycleEvent.BEFORE_LOAD, callback=callback)
        lc.add_hook(hook)
        assert lc.remove_hook(LifecycleEvent.BEFORE_LOAD, callback) is True

    def test_add_listener(self):
        lc = LifecycleManager()
        listener = lambda e, p: None
        lc.add_listener(listener)
        assert len(lc._listeners) == 1

    def test_remove_listener(self):
        lc = LifecycleManager()
        listener = lambda e, p: None
        lc.add_listener(listener)
        assert lc.remove_listener(listener) is True

    def test_hook_fired_on_load(self):
        lc = LifecycleManager()
        fired = []
        callback = lambda p: fired.append("loaded")
        lc.add_hook(LifecycleHook(event=LifecycleEvent.AFTER_LOAD, callback=callback))
        lc.start(Plugin(PluginMetadata(id="test", name="Test")))
        assert "loaded" in fired

    def test_event_log(self):
        lc = LifecycleManager()
        lc.start(Plugin(PluginMetadata(id="test", name="Test")))
        log = lc.get_event_log()
        assert len(log) >= 4  # before_load, after_load, before_init, after_init

    def test_clear_log(self):
        lc = LifecycleManager()
        lc.start(Plugin(PluginMetadata(id="test", name="Test")))
        lc.clear_log()
        assert len(lc.get_event_log()) == 0


# ==================== Dependency Resolver Tests ====================

class TestDependencyGraph:
    def test_add_plugin(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b", "c"])
        assert graph.get_dependencies("a") == ["b", "c"]

    def test_remove_plugin(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("b", [])
        assert graph.remove_plugin("a") is True
        # b still exists as its own plugin
        assert "b" in graph.get_all()
        assert graph.get_dependents("b") == []

    def test_get_dependents(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("c", ["b"])
        dependents = graph.get_dependents("b")
        assert "a" in dependents
        assert "c" in dependents

    def test_get_all(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("c", [])
        all_plugins = graph.get_all()
        assert "a" in all_plugins
        assert "b" in all_plugins
        assert "c" in all_plugins


class TestDependencyResolver:
    def test_resolve_load_order_linear(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("b", ["c"])
        graph.add_plugin("c", [])
        resolver = DependencyResolver(graph)
        order = resolver.resolve_load_order()
        assert order.index("c") < order.index("b")
        assert order.index("b") < order.index("a")

    def test_resolve_load_order_diamond(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b", "c"])
        graph.add_plugin("b", ["d"])
        graph.add_plugin("c", ["d"])
        graph.add_plugin("d", [])
        resolver = DependencyResolver(graph)
        order = resolver.resolve_load_order()
        assert order.index("d") < order.index("b")
        assert order.index("d") < order.index("c")

    def test_resolve_unload_order(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("b", ["c"])
        graph.add_plugin("c", [])
        resolver = DependencyResolver(graph)
        order = resolver.resolve_unload_order()
        # Unload order is reverse of load order
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_detect_cycles_none(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("b", ["c"])
        graph.add_plugin("c", [])
        resolver = DependencyResolver(graph)
        cycles = resolver.detect_cycles()
        assert len(cycles) == 0

    def test_detect_cycles_simple(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("b", ["a"])
        resolver = DependencyResolver(graph)
        cycles = resolver.detect_cycles()
        assert len(cycles) >= 1

    def test_get_missing_dependencies(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b", "c"])
        graph.add_plugin("b", [])
        resolver = DependencyResolver(graph)
        missing = resolver.get_missing_dependencies("a", {"b"})
        assert "c" in missing

    def test_get_dependents_to_stop(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("c", ["b"])
        graph.add_plugin("d", ["a"])
        resolver = DependencyResolver(graph)
        dependents = resolver.get_dependents_to_stop("b")
        assert "a" in dependents
        assert "c" in dependents

    def test_can_unload(self):
        graph = DependencyGraph()
        graph.add_plugin("a", ["b"])
        graph.add_plugin("b", [])
        resolver = DependencyResolver(graph)
        assert resolver.can_unload("a") is True
        assert resolver.can_unload("b") is False


# ==================== Config Tests ====================

class TestPluginConfig:
    def test_create(self):
        config = PluginConfig(plugin_id="test")
        assert config.plugin_id == "test"
        assert config.enabled is True

    def test_get_set(self):
        config = PluginConfig(plugin_id="test")
        config.set("key", "value")
        assert config.get("key") == "value"

    def test_get_default(self):
        config = PluginConfig(plugin_id="test")
        assert config.get("nonexistent", "default") == "default"

    def test_merge(self):
        config = PluginConfig(plugin_id="test", values={"a": 1})
        other = PluginConfig(plugin_id="test", values={"b": 2})
        config.merge(other)
        assert config.get("a") == 1
        assert config.get("b") == 2

    def test_to_dict(self):
        config = PluginConfig(plugin_id="test", values={"key": "val"})
        d = config.to_dict()
        assert d["plugin_id"] == "test"
        assert d["values"]["key"] == "val"


class TestConfigValidator:
    def test_register_schema(self):
        validator = ConfigValidator()
        validator.register_schema("test", {"required": ["name"]})
        assert validator.get_schema("test") is not None

    def test_validate_valid(self):
        validator = ConfigValidator()
        validator.register_schema("test", {
            "required": ["name"],
            "properties": {"name": {"type": "string"}}
        })
        valid, errors = validator.validate("test", {"name": "Alice"})
        assert valid is True
        assert len(errors) == 0

    def test_validate_missing_required(self):
        validator = ConfigValidator()
        validator.register_schema("test", {"required": ["name"]})
        valid, errors = validator.validate("test", {})
        assert valid is False
        assert len(errors) == 1

    def test_validate_wrong_type(self):
        validator = ConfigValidator()
        validator.register_schema("test", {
            "properties": {"count": {"type": "integer"}}
        })
        valid, errors = validator.validate("test", {"count": "not_a_number"})
        assert valid is False

    def test_validate_enum(self):
        validator = ConfigValidator()
        validator.register_schema("test", {
            "properties": {"level": {"enum": ["low", "medium", "high"]}}
        })
        valid, errors = validator.validate("test", {"level": "invalid"})
        assert valid is False

    def test_validate_no_schema(self):
        validator = ConfigValidator()
        valid, errors = validator.validate("nonexistent", {"key": "value"})
        assert valid is True

    def test_validate_min_max(self):
        validator = ConfigValidator()
        validator.register_schema("test", {
            "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 100}}
        })
        valid, errors = validator.validate("test", {"score": 150})
        assert valid is False
        valid, errors = validator.validate("test", {"score": -5})
        assert valid is False


# ==================== Health Monitor Tests ====================

class TestHealthStatus:
    def test_status_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestHealthCheckResult:
    def test_create(self):
        result = HealthCheckResult(plugin_id="test", status=HealthStatus.HEALTHY)
        assert result.plugin_id == "test"
        assert result.is_healthy is True

    def test_unhealthy(self):
        result = HealthCheckResult(plugin_id="test", status=HealthStatus.UNHEALTHY)
        assert result.is_healthy is False


class TestHealthMonitor:
    def test_check_health(self):
        monitor = HealthMonitor()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        result = monitor.check_health(plugin)
        assert result.plugin_id == "test"
        assert result.is_healthy is True

    def test_get_status(self):
        monitor = HealthMonitor()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        monitor.check_health(plugin)
        status = monitor.get_status("test")
        assert status is not None
        assert status.plugin_id == "test"

    def test_get_history(self):
        monitor = HealthMonitor()
        meta = PluginMetadata(id="test", name="Test")
        plugin = Plugin(meta)
        monitor.check_health(plugin)
        monitor.check_health(plugin)
        history = monitor.get_history("test")
        assert len(history) == 2

    def test_get_all_statuses(self):
        monitor = HealthMonitor()
        p1 = Plugin(PluginMetadata(id="t1", name="T1"))
        p2 = Plugin(PluginMetadata(id="t2", name="T2"))
        monitor.check_health(p1)
        monitor.check_health(p2)
        statuses = monitor.get_all_statuses()
        assert len(statuses) == 2

    def test_get_healthy(self):
        monitor = HealthMonitor()
        p1 = Plugin(PluginMetadata(id="t1", name="T1"))
        monitor.check_health(p1)
        healthy = monitor.get_healthy()
        assert "t1" in healthy

    def test_get_unhealthy(self):
        monitor = HealthMonitor()
        p1 = Plugin(PluginMetadata(id="t1", name="T1"))
        monitor.check_health(p1)
        unhealthy = monitor.get_unhealthy()
        assert len(unhealthy) == 0

    def test_get_overall_status(self):
        monitor = HealthMonitor()
        p1 = Plugin(PluginMetadata(id="t1", name="T1"))
        monitor.check_health(p1)
        assert monitor.get_overall_status() == HealthStatus.HEALTHY

    def test_get_overall_status_unknown(self):
        monitor = HealthMonitor()
        assert monitor.get_overall_status() == HealthStatus.UNKNOWN

    def test_clear(self):
        monitor = HealthMonitor()
        p1 = Plugin(PluginMetadata(id="t1", name="T1"))
        monitor.check_health(p1)
        monitor.clear()
        assert len(monitor.get_all_statuses()) == 0


# ==================== Versioning Tests ====================

class TestVersion:
    def test_parse(self):
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_prerelease(self):
        v = Version.parse("1.0.0-beta")
        assert v.prerelease == "beta"

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            Version.parse("invalid")

    def test_str(self):
        v = Version(1, 2, 3)
        assert str(v) == "1.2.3"

    def test_str_prerelease(self):
        v = Version(1, 0, 0, "alpha")
        assert str(v) == "1.0.0-alpha"

    def test_equality(self):
        v1 = Version.parse("1.2.3")
        v2 = Version.parse("1.2.3")
        assert v1 == v2

    def test_less_than(self):
        v1 = Version.parse("1.0.0")
        v2 = Version.parse("2.0.0")
        assert v1 < v2

    def test_greater_than(self):
        v1 = Version.parse("2.0.0")
        v2 = Version.parse("1.0.0")
        assert v1 > v2

    def test_prerelease_less_than_release(self):
        v1 = Version.parse("1.0.0-alpha")
        v2 = Version.parse("1.0.0")
        assert v1 < v2

    def test_is_compatible_with(self):
        v1 = Version.parse("1.2.3")
        v2 = Version.parse("1.5.0")
        assert v1.is_compatible_with(v2) is True

    def test_is_not_compatible_with(self):
        v1 = Version.parse("1.0.0")
        v2 = Version.parse("2.0.0")
        assert v1.is_compatible_with(v2) is False


class TestVersionRange:
    def test_contains(self):
        range_obj = VersionRange(min_version=Version.parse("1.0.0"), max_version=Version.parse("2.0.0"))
        assert range_obj.contains(Version.parse("1.5.0")) is True
        assert range_obj.contains(Version.parse("2.1.0")) is False

    def test_contains_inclusive(self):
        range_obj = VersionRange(min_version=Version.parse("1.0.0"), min_inclusive=True)
        assert range_obj.contains(Version.parse("1.0.0")) is True

    def test_contains_exclusive(self):
        range_obj = VersionRange(min_version=Version.parse("1.0.0"), min_inclusive=False)
        assert range_obj.contains(Version.parse("1.0.0")) is False

    def test_str(self):
        range_obj = VersionRange(min_version=Version.parse("1.0.0"), max_version=Version.parse("2.0.0"))
        s = str(range_obj)
        assert ">=" in s
        assert "<=" in s


class TestCompatibility:
    def test_check_version_compatible(self):
        assert Compatibility.check_version_compatibility("1.2.3", "1.0.0") is True

    def test_check_version_incompatible(self):
        assert Compatibility.check_version_compatibility("2.0.0", "1.0.0") is False

    def test_is_api_compatible(self):
        assert Compatibility.is_api_compatible("1.2.0", "1.5.0") is True

    def test_is_api_incompatible(self):
        assert Compatibility.is_api_compatible("2.0.0", "1.0.0") is False

    def test_check_range(self):
        assert Compatibility.check_range("1.5.0", ">=1.0.0 <=2.0.0") is True

    def test_check_range_outside(self):
        assert Compatibility.check_range("3.0.0", ">=1.0.0 <=2.0.0") is False
