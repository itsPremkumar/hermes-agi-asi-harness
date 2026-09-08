"""Tests for EventDispatcher."""
import pytest

from src.harness.runtime.event_dispatcher import EventDispatcher, Event


class TestEventDispatcher:
    def test_init(self):
        ed = EventDispatcher()
        assert ed.get_handler_count() == 0

    def test_on_dispatch(self):
        ed = EventDispatcher()
        results = []
        ed.on("test", lambda e: results.append(e.data))
        ed.dispatch("test", data="hello")
        assert results == ["hello"]

    def test_multiple_handlers(self):
        ed = EventDispatcher()
        results = []
        ed.on("test", lambda e: results.append("a"))
        ed.on("test", lambda e: results.append("b"))
        ed.dispatch("test")
        assert sorted(results) == ["a", "b"]

    def test_priority_ordering(self):
        ed = EventDispatcher()
        results = []
        ed.on("test", lambda e: results.append("low"), priority=0)
        ed.on("test", lambda e: results.append("high"), priority=10)
        ed.on("test", lambda e: results.append("mid"), priority=5)
        ed.dispatch("test")
        assert results == ["high", "mid", "low"]

    def test_once_handler(self):
        ed = EventDispatcher()
        results = []
        ed.once("test", lambda e: results.append("once"))
        ed.dispatch("test")
        ed.dispatch("test")
        assert results == ["once"]

    def test_on_any_handler(self):
        ed = EventDispatcher()
        results = []
        ed.on_any(lambda e: results.append(e.name))
        ed.dispatch("event1")
        ed.dispatch("event2")
        assert results == ["event1", "event2"]

    def test_off_specific_handler(self):
        ed = EventDispatcher()
        results = []
        handler = lambda e: results.append("data")
        ed.on("test", handler)
        ed.off("test", handler)
        ed.dispatch("test")
        assert results == []

    def test_off_all_handlers(self):
        ed = EventDispatcher()
        results = []
        ed.on("test", lambda e: results.append("a"))
        ed.on("test", lambda e: results.append("b"))
        ed.off("test")
        ed.dispatch("test")
        assert results == []

    def test_off_missing_event(self):
        ed = EventDispatcher()
        assert ed.off("missing") is False

    def test_has_handlers_true(self):
        ed = EventDispatcher()
        ed.on("test", lambda e: None)
        assert ed.has_handlers("test") is True

    def test_has_handlers_false(self):
        ed = EventDispatcher()
        assert ed.has_handlers("test") is False

    def test_get_handler_count_specific(self):
        ed = EventDispatcher()
        ed.on("test", lambda e: None)
        ed.on("test", lambda e: None)
        ed.on("other", lambda e: None)
        assert ed.get_handler_count("test") == 2

    def test_get_handler_count_all(self):
        ed = EventDispatcher()
        ed.on("test", lambda e: None)
        ed.on("other", lambda e: None)
        ed.on_any(lambda e: None)
        assert ed.get_handler_count() == 3

    def test_get_event_names(self):
        ed = EventDispatcher()
        ed.on("event1", lambda e: None)
        ed.on("event2", lambda e: None)
        assert ed.get_event_names() == {"event1", "event2"}

    def test_event_cancelled(self):
        ed = EventDispatcher()
        results = []
        def cancel_handler(e):
            e.cancel()
            results.append("canceller")
        def skipped_handler(e):
            results.append("should_not_run")
        ed.on("test", cancel_handler, priority=10)
        ed.on("test", skipped_handler, priority=0)
        ed.dispatch("test")
        assert "should_not_run" not in results

    def test_event_filter(self):
        ed = EventDispatcher()
        results = []
        ed.on("test", lambda e: results.append(e.data), filter_fn=lambda e: e.data > 5)
        ed.dispatch("test", data=3)
        ed.dispatch("test", data=10)
        assert results == [10]

    def test_history(self):
        ed = EventDispatcher()
        ed.dispatch("event1", data="a")
        ed.dispatch("event2", data="b")
        history = ed.get_history()
        assert len(history) == 2
        assert history[0].name == "event1"
        assert history[1].name == "event2"

    def test_history_filtered(self):
        ed = EventDispatcher()
        ed.dispatch("event1")
        ed.dispatch("event2")
        ed.dispatch("event1")
        history = ed.get_history("event1")
        assert len(history) == 2

    def test_history_limit(self):
        ed = EventDispatcher()
        for i in range(10):
            ed.dispatch("event")
        history = ed.get_history(limit=5)
        assert len(history) == 5

    def test_clear_history(self):
        ed = EventDispatcher()
        ed.dispatch("event")
        ed.clear_history()
        assert len(ed.get_history()) == 0

    def test_remove_all_listeners_specific(self):
        ed = EventDispatcher()
        ed.on("test", lambda e: None)
        ed.on("other", lambda e: None)
        ed.remove_all_listeners("test")
        assert ed.has_handlers("test") is False
        assert ed.has_handlers("other") is True

    def test_remove_all_listeners_all(self):
        ed = EventDispatcher()
        ed.on("test", lambda e: None)
        ed.on_any(lambda e: None)
        ed.remove_all_listeners()
        assert ed.get_handler_count() == 0

    def test_event_source(self):
        ed = EventDispatcher()
        results = []
        ed.on("test", lambda e: results.append(e.source))
        ed.dispatch("test", source="mysource")
        assert results == ["mysource"]

    def test_handler_exception_doesnt_break(self):
        ed = EventDispatcher()
        results = []
        ed.on("test", lambda e: 1/0)  # noqa: E501
        ed.on("test", lambda e: results.append("ok"))
        ed.dispatch("test")
        assert results == ["ok"]

    def test_max_history(self):
        ed = EventDispatcher(max_history=5)
        for i in range(10):
            ed.dispatch("event")
        assert len(ed.get_history()) == 5

    def test_decorator_usage(self):
        ed = EventDispatcher()
        results = []
        decorator = ed.on_decorator("test")
        @decorator
        def handler(e):
            results.append(e.data)
        ed.dispatch("test", data="decorated")
        assert results == ["decorated"]
