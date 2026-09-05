"""Tests for memory/ — Memory Layer."""

from __future__ import annotations

import pytest

from src.harness.memory import (
    EmbeddingModel,
    LongTermMemory,
    MemoryEntry,
    MemoryLayer,
    ShortTermMemory,
)


class TestMemoryEntry:
    """Tests for MemoryEntry."""

    def test_create(self):
        entry = MemoryEntry(content="hello")
        assert entry.content == "hello"
        assert entry.entry_id is not None


class TestEmbeddingModel:
    """Tests for EmbeddingModel."""

    def test_embed(self):
        em = EmbeddingModel(dimension=32)
        v = em.embed("hello")
        assert len(v) == 32

    def test_embed_deterministic(self):
        em = EmbeddingModel(dimension=16)
        v1 = em.embed("test")
        v2 = em.embed("test")
        assert v1 == v2

    def test_embed_different_texts(self):
        em = EmbeddingModel(dimension=16)
        v1 = em.embed("hello")
        v2 = em.embed("world")
        assert v1 != v2

    def test_cosine_similarity(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert EmbeddingModel.cosine_similarity(a, b) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert EmbeddingModel.cosine_similarity(a, b) == pytest.approx(0.0)

    def test_embed_batch(self):
        em = EmbeddingModel(dimension=8)
        vectors = em.embed_batch(["a", "b", "c"])
        assert len(vectors) == 3
        assert all(len(v) == 8 for v in vectors)


class TestShortTermMemory:
    """Tests for ShortTermMemory."""

    def test_create(self):
        stm = ShortTermMemory()
        assert stm.size == 0

    def test_add(self):
        stm = ShortTermMemory()
        stm.add("hello")
        assert stm.size == 1

    def test_recall(self):
        stm = ShortTermMemory()
        stm.add("a")
        stm.add("b")
        entries = stm.recall(n=1)
        assert len(entries) == 1

    def test_max_entries(self):
        stm = ShortTermMemory(max_entries=3)
        for i in range(5):
            stm.add(f"item{i}")
        assert stm.size == 3

    def test_clear(self):
        stm = ShortTermMemory()
        stm.add("hello")
        stm.clear()
        assert stm.size == 0


class TestLongTermMemory:
    """Tests for LongTermMemory."""

    def test_create(self):
        ltm = LongTermMemory()
        assert ltm.size == 0

    def test_store(self):
        ltm = LongTermMemory()
        entry = ltm.store("important info")
        assert entry.entry_id is not None

    def test_retrieve(self):
        ltm = LongTermMemory()
        ltm.store("Python is great")
        results = ltm.retrieve("Python")
        assert len(results) > 0

    def test_clear(self):
        ltm = LongTermMemory()
        ltm.store("info")
        ltm.clear()
        assert ltm.size == 0


class TestMemoryLayer:
    """Tests for MemoryLayer."""

    def test_create(self):
        ml = MemoryLayer()
        assert ml.short_term.size == 0
        assert ml.long_term.size == 0

    def test_remember(self):
        ml = MemoryLayer()
        ml.remember("important fact", importance=0.9)
        assert ml.short_term.size == 1

    def test_recall_recent(self):
        ml = MemoryLayer()
        ml.remember("fact1")
        ml.remember("fact2")
        recent = ml.recall_recent(n=2)
        assert len(recent) == 2

    def test_recall_relevant(self):
        ml = MemoryLayer()
        ml.remember("Machine learning is fascinating", importance=0.9, long_term=True)
        results = ml.recall_relevant("machine learning")
        assert len(results) > 0

    def test_consolidate(self):
        ml = MemoryLayer()
        ml.remember("important", importance=0.8, long_term=False)
        count = ml.consolidate()
        assert count == 1

    def test_clear_all(self):
        ml = MemoryLayer()
        ml.remember("info")
        ml.clear_all()
        assert ml.short_term.size == 0
        assert ml.long_term.size == 0
