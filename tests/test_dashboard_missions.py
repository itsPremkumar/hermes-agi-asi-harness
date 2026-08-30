"""Tests for MissionController."""
import pytest
from core.dashboard.missions import MissionController, MissionStatus


class TestMissionController:
    def test_create(self):
        mc = MissionController()
        assert mc.count() == 0

    def test_create_mission(self):
        mc = MissionController()
        m = mc.create("Build REST API")
        assert m.goal == "Build REST API"
        assert m.status == MissionStatus.PENDING
        assert mc.count() == 1

    def test_start(self):
        mc = MissionController()
        m = mc.create("test")
        assert mc.start(m.id) is True
        assert mc.get(m.id).status == MissionStatus.RUNNING

    def test_complete(self):
        mc = MissionController()
        m = mc.create("test")
        assert mc.complete(m.id, result="done") is True
        completed = mc.get(m.id)
        assert completed.status == MissionStatus.COMPLETED
        assert completed.result == "done"

    def test_fail(self):
        mc = MissionController()
        m = mc.create("test")
        assert mc.fail(m.id, error="OOM") is True
        failed = mc.get(m.id)
        assert failed.status == MissionStatus.FAILED
        assert failed.error == "OOM"

    def test_get(self):
        mc = MissionController()
        m = mc.create("test")
        result = mc.get(m.id)
        assert result is not None
        assert result.goal == "test"

    def test_list_all(self):
        mc = MissionController()
        mc.create("a")
        mc.create("b")
        assert len(mc.list_all()) == 2

    def test_list_by_status(self):
        mc = MissionController()
        m1 = mc.create("a")
        m2 = mc.create("b")
        mc.start(m1.id)
        running = mc.list_by_status(MissionStatus.RUNNING)
        assert len(running) == 1

    def test_full_lifecycle(self):
        mc = MissionController()
        m = mc.create("Build API")
        assert m.status == MissionStatus.PENDING
        mc.start(m.id)
        assert mc.get(m.id).status == MissionStatus.RUNNING
        mc.complete(m.id)
        assert mc.get(m.id).status == MissionStatus.COMPLETED

    def test_get_state(self):
        mc = MissionController()
        m = mc.create("test")
        mc.start(m.id)
        state = mc.get_state()
        assert state["total"] == 1
        assert state["running"] == 1
