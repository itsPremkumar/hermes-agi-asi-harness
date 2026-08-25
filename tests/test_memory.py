"""Tests for src/reflexion_eval/memory.py."""
from __future__ import annotations

import pytest

from reflexion_eval.memory import MemoryStore, Reflection


# ---------------------------------------------------------------------------
# Reflection dataclass
# ---------------------------------------------------------------------------
class TestReflection:
    def test_to_dict_roundtrip(self):
        r = Reflection(
            task_id="t1",
            attempt="answer",
            score=0.8,
            feedback="good",
            reflection="could be better",
            order=0,
        )
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["score"] == 0.8
        assert d["order"] == 0

    def test_from_dict_roundtrip(self):
        r = Reflection(
            task_id="t1",
            attempt="answer",
            score=0.5,
            feedback="ok",
            reflection="fix it",
        )
        d = r.to_dict()
        r2 = Reflection.from_dict(d)
        assert r2.task_id == r.task_id
        assert r2.attempt == r.attempt
        assert r2.score == r.score
        assert r2.feedback == r.feedback
        assert r2.reflection == r.reflection


# ---------------------------------------------------------------------------
# MemoryStore core
# ---------------------------------------------------------------------------
class TestMemoryStoreAddGet:
    def test_add_and_get(self):
        store = MemoryStore()
        r = Reflection(task_id="t1", attempt="a", score=0.5, feedback="f", reflection="r")
        store.add(r)
        assert len(store) == 1
        got = store.get("t1")
        assert len(got) == 1
        assert got[0].attempt == "a"

    def test_get_empty(self):
        store = MemoryStore()
        assert store.get("nope") == []

    def test_len_counts_all_tasks(self):
        store = MemoryStore()
        store.add(Reflection("t1", "a", 0.5, "f", "r"))
        store.add(Reflection("t1", "b", 0.3, "f", "r"))
        store.add(Reflection("t2", "c", 0.9, "f", "r"))
        assert len(store) == 3

    def test_contains(self):
        store = MemoryStore()
        store.add(Reflection("t1", "a", 0.5, "f", "r"))
        assert "t1" in store
        assert "t2" not in store

    def test_order_is_incremental(self):
        store = MemoryStore()
        for i in range(3):
            store.add(Reflection("t1", f"a{i}", 0.5, "f", "r"))
        reflections = store.get("t1")
        assert [r.order for r in reflections] == [0, 1, 2]

    def test_iter_yields_all(self):
        store = MemoryStore()
        store.add(Reflection("t1", "a", 0.5, "f", "r"))
        store.add(Reflection("t2", "b", 0.6, "f", "r"))
        items = list(store)
        assert len(items) == 2


# ---------------------------------------------------------------------------
# MemoryStore clear
# ---------------------------------------------------------------------------
class TestMemoryStoreClear:
    def test_clear_specific_task(self):
        store = MemoryStore()
        store.add(Reflection("t1", "a", 0.5, "f", "r"))
        store.add(Reflection("t2", "b", 0.6, "f", "r"))
        store.clear("t1")
        assert "t1" not in store
        assert "t2" in store
        assert len(store) == 1

    def test_clear_all(self):
        store = MemoryStore()
        store.add(Reflection("t1", "a", 0.5, "f", "r"))
        store.add(Reflection("t2", "b", 0.6, "f", "r"))
        store.clear()
        assert len(store) == 0


# ---------------------------------------------------------------------------
# MemoryStore serialization
# ---------------------------------------------------------------------------
class TestMemoryStoreSerialization:
    def test_save_and_load_roundtrip(self):
        store = MemoryStore()
        store.add(Reflection("t1", "a1", 0.5, "fb1", "ref1", order=0))
        store.add(Reflection("t1", "a2", 0.8, "fb2", "ref2", order=1))
        data = store.save()
        assert len(data) == 2

        store2 = MemoryStore.load(data)
        assert len(store2) == 2
        reflections = store2.get("t1")
        assert len(reflections) == 2
        assert reflections[0].attempt == "a1"
        assert reflections[1].attempt == "a2"

    def test_load_empty(self):
        store = MemoryStore.load(None)
        assert len(store) == 0

    def test_load_empty_list(self):
        store = MemoryStore.load([])
        assert len(store) == 0


# ---------------------------------------------------------------------------
# format_history
# ---------------------------------------------------------------------------
class TestFormatHistory:
    def test_format_history_empty(self):
        store = MemoryStore()
        assert store.format_history("t1") == ""

    def test_format_history_with_entries(self):
        store = MemoryStore()
        store.add(Reflection("t1", "attempt1", 0.5, "feedback1", "reflection1"))
        store.add(Reflection("t1", "attempt2", 0.7, "feedback2", "reflection2"))
        hist = store.format_history("t1")
        assert "attempt1" in hist
        assert "feedback1" in hist
        assert "reflection1" in hist
        assert "attempt2" in hist

    def test_format_history_limit(self):
        store = MemoryStore()
        for i in range(5):
            store.add(Reflection("t1", f"attempt{i}", 0.5, "f", "r"))
        hist = store.format_history("t1", limit=2)
        assert "attempt3" in hist
        assert "attempt4" in hist
        assert "attempt0" not in hist

    def test_format_history_no_cross_task_leak(self):
        store = MemoryStore()
        store.add(Reflection("t1", "t1-attempt", 0.5, "t1-fb", "t1-ref"))
        store.add(Reflection("t2", "t2-attempt", 0.5, "t2-fb", "t2-ref"))
        hist = store.format_history("t1")
        assert "t1-attempt" in hist
        assert "t2-attempt" not in hist
