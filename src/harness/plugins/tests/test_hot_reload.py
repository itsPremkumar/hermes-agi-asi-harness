"""Tests for Plugin Hot-Reload System."""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from harness.plugins.hot_reload import (
    PluginHotReloader,
    ReloadStatus,
    ReloadEvent,
    PluginSnapshot,
)


class TestPluginHotReloader:
    def test_create(self):
        hr = PluginHotReloader()
        assert hr is not None

    def test_snapshot(self):
        hr = PluginHotReloader()
        hr.snapshot("p1", "p1.py", "code", {}, "active")
        assert "p1" in hr.get_snapshots()

    def test_get_snapshots(self):
        hr = PluginHotReloader()
        hr.snapshot("p1", "p1.py", "code", {}, "active")
        hr.snapshot("p2", "p2.py", "code2", {}, "active")
        assert len(hr.get_snapshots()) == 2

    def test_register_callback(self):
        hr = PluginHotReloader()
        events = []
        hr.register_callback(lambda e: events.append(e))
        assert len(hr._callbacks) == 1

    def test_reload_plugin_not_found(self):
        hr = PluginHotReloader()
        event = hr.reload_plugin("nonexistent", "/nonexistent/path.py")
        assert event.status == ReloadStatus.FAILED

    def test_rollback_no_snapshot(self):
        hr = PluginHotReloader()
        event = hr.rollback("nonexistent")
        assert event.status == ReloadStatus.FAILED

    def test_history(self):
        hr = PluginHotReloader()
        hr.reload_plugin("nonexistent", "/nonexistent/path.py")
        assert len(hr.get_history()) == 1

    def test_start_stop_watching(self, tmp_path):
        hr = PluginHotReloader()
        f = tmp_path / "plugin.py"
        f.write_text("x = 1")
        hr.start_watching("p1", str(f))
        assert "p1" in hr._watchers
        hr.stop_watching("p1")
        assert "p1" not in hr._watchers

    def test_stop_all(self, tmp_path):
        hr = PluginHotReloader()
        f1 = tmp_path / "plugin1.py"
        f2 = tmp_path / "plugin2.py"
        f1.write_text("x = 1")
        f2.write_text("x = 2")
        hr.start_watching("p1", str(f1))
        hr.start_watching("p2", str(f2))
        assert len(hr._watchers) == 2
        hr.stop_all()
        assert len(hr._watchers) == 0


class TestReloadEvent:
    def test_create(self):
        event = ReloadEvent("p1", ReloadStatus.SUCCESS, time.time())
        assert event.plugin_id == "p1"
        assert event.status == ReloadStatus.SUCCESS


class TestPluginSnapshot:
    def test_create(self):
        snap = PluginSnapshot("p1", "p1.py", "code", {}, "active")
        assert snap.plugin_id == "p1"
        assert snap.source_code == "code"
