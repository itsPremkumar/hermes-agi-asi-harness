"""Tests for EventLog."""
from core.dashboard.events import EventLog, EventLevel


class TestEventLog:
    def test_create(self):
        el = EventLog()
        assert el.count() == 0

    def test_log(self):
        el = EventLog()
        e = el.log("test message", EventLevel.INFO)
        assert e.message == "test message"
        assert e.level == EventLevel.INFO
        assert el.count() == 1

    def test_info(self):
        el = EventLog()
        e = el.info("info msg")
        assert e.level == EventLevel.INFO

    def test_success(self):
        el = EventLog()
        e = el.success("done")
        assert e.level == EventLevel.SUCCESS

    def test_warning(self):
        el = EventLog()
        e = el.warning("warn")
        assert e.level == EventLevel.WARNING

    def test_error(self):
        el = EventLog()
        e = el.error("err")
        assert e.level == EventLevel.ERROR

    def test_get_all(self):
        el = EventLog()
        el.info("a")
        el.info("b")
        assert len(el.get_all()) == 2

    def test_get_by_level(self):
        el = EventLog()
        el.info("a")
        el.error("b")
        assert len(el.get_by_level(EventLevel.ERROR)) == 1

    def test_get_by_source(self):
        el = EventLog()
        el.info("a", source="plugin")
        el.info("b", source="system")
        assert len(el.get_by_source("plugin")) == 1

    def test_get_recent(self):
        el = EventLog()
        for i in range(10):
            el.info(f"msg {i}")
        recent = el.get_recent(5)
        assert len(recent) == 5

    def test_clear(self):
        el = EventLog()
        el.info("a")
        el.clear()
        assert el.count() == 0

    def test_get_state(self):
        el = EventLog()
        el.info("a")
        el.error("b")
        state = el.get_state()
        assert state["total"] == 2
        assert state["info"] == 1
        assert state["error"] == 1
