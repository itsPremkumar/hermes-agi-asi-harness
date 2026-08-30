"""Tests for plugins/ — Plugin/Hook System."""

from __future__ import annotations

import pytest

from src.harness.plugins import (
    Hook,
    HookRegistry,
    LifecycleHooks,
    PluginBase,
    PluginManager,
)


class TestHook:
    """Tests for Hook."""

    def test_create_hook(self):
        h = Hook(name="test", func=lambda: None)
        assert h.name == "test"
        assert h.priority == 0


class TestHookRegistry:
    """Tests for HookRegistry."""

    def test_register_and_fire(self):
        hr = HookRegistry()
        results = []
        hr.register("event", lambda: results.append(1))
        hr.fire("event")
        assert results == [1]

    def test_fire_with_kwargs(self):
        hr = HookRegistry()
        results = []
        hr.register("event", lambda x: results.append(x))
        hr.fire("event", x=42)
        assert results == [42]

    def test_priority_ordering(self):
        hr = HookRegistry()
        results = []
        hr.register("event", lambda: results.append("low"), priority=0)
        hr.register("event", lambda: results.append("high"), priority=10)
        hr.fire("event")
        assert results == ["high", "low"]

    def test_unregister(self):
        hr = HookRegistry()
        func = lambda: None
        hr.register("event", func)
        assert hr.unregister("event", func) is True

    def test_clear_event(self):
        hr = HookRegistry()
        hr.register("event", lambda: None)
        hr.clear_event("event")
        assert "event" not in hr.events

    def test_clear_all(self):
        hr = HookRegistry()
        hr.register("e1", lambda: None)
        hr.register("e2", lambda: None)
        hr.clear_all()
        assert hr.events == []

    def test_events_property(self):
        hr = HookRegistry()
        hr.register("event", lambda: None)
        assert "event" in hr.events


class TestLifecycleHooks:
    """Tests for LifecycleHooks."""

    def test_has_standard_events(self):
        assert LifecycleHooks.ON_LOAD == "on_load"
        assert LifecycleHooks.ON_START == "on_start"
        assert LifecycleHooks.ON_STOP == "on_stop"


class TestPluginBase:
    """Tests for PluginBase."""

    def test_create_plugin(self):
        p = PluginBase("test", "Test Plugin")
        assert p.plugin_id == "test"
        assert p.name == "Test Plugin"

    def test_is_active_default(self):
        p = PluginBase("test", "Test")
        assert p.is_active is False

    def test_on_start_activates(self):
        p = PluginBase("test", "Test")
        p.on_start()
        assert p.is_active is True

    def test_on_stop_deactivates(self):
        p = PluginBase("test", "Test")
        p.on_start()
        p.on_stop()
        assert p.is_active is False

    def test_register_and_fire_hook(self):
        p = PluginBase("test", "Test")
        results = []
        p.register_hook("custom", lambda: results.append(1))
        p.fire_hook("custom")
        assert results == [1]

    def test_get_info(self):
        p = PluginBase("test", "Test", version="1.0.0")
        info = p.get_info()
        assert info["plugin_id"] == "test"
        assert info["version"] == "1.0.0"


class TestPluginManager:
    """Tests for PluginManager."""

    def test_register_and_get(self):
        pm = PluginManager()
        p = PluginBase("test", "Test")
        pm.register(p)
        assert pm.get("test") == p

    def test_start_stop(self):
        pm = PluginManager()
        p = PluginBase("test", "Test")
        pm.register(p)
        pm.start("test")
        assert p.is_active is True
        pm.stop("test")
        assert p.is_active is False

    def test_list_plugins(self):
        pm = PluginManager()
        pm.register(PluginBase("p1", "Plugin 1"))
        pm.register(PluginBase("p2", "Plugin 2"))
        plugins = pm.list_plugins()
        assert len(plugins) == 2

    def test_unregister(self):
        pm = PluginManager()
        p = PluginBase("test", "Test")
        pm.register(p)
        removed = pm.unregister("test")
        assert removed == p
        assert pm.get("test") is None

    def test_fire_global(self):
        pm = PluginManager()
        results = []
        pm.register_global_hook("event", lambda: results.append(1))
        pm.fire_global("event")
        assert results == [1]
