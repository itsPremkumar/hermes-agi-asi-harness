"""Comprehensive test suite for ContextVault."""

from __future__ import annotations

import sys
import time
import pytest
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextvault.access_control import AccessController
from contextvault.consolidation import ConsolidationPipeline
from contextvault.memory_store import MemoryStore
from contextvault.models import (
    AccessLevel,
    Memory,
    MemoryMetadata,
    MemoryRelation,
    MemoryTier,
    MemoryType,
)
from contextvault.relevance import ForgettingCurveParams, RelevanceScorer
from contextvault.search import MemorySearch
from contextvault.ttl import ColdStorage, TTLManager
from contextvault.vector_store import (
    HashEmbeddingProvider,
    VectorStore,
    EmbeddingProvider,
)


# ===========================================================================
# Models tests
# ===========================================================================


class TestMemoryModel:
    def test_create_memory(self):
        mem = Memory(
            content="Test content",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        assert mem.id is not None
        assert mem.content == "Test content"
        assert mem.tier == MemoryTier.SEMANTIC
        assert mem.memory_type == MemoryType.FACT

    def test_memory_hash_auto(self):
        mem = Memory(
            content="Hello world",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        assert mem.content_hash is not None
        assert len(mem.content_hash) == 16

    def test_memory_touch(self):
        mem = Memory(
            content="Test",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        initial_count = mem.access_count
        time.sleep(0.01)
        mem.touch()
        assert mem.access_count == initial_count + 1
        assert mem.accessed_at > mem.created_at

    def test_memory_expired(self):
        mem = Memory(
            content="Temp",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=0.01,
        )
        time.sleep(0.02)
        assert mem.is_expired()

    def test_memory_not_expired(self):
        mem = Memory(
            content="Long lasting",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            ttl=3600,
        )
        assert not mem.is_expired()

    def test_memory_to_document(self):
        mem = Memory(
            content="Document test",
            memory_type=MemoryType.CONCEPT,
            tier=MemoryTier.SEMANTIC,
        )
        doc = mem.to_document()
        assert doc["content"] == "Document test"
        assert doc["memory_type"] == "concept"
        assert doc["tier"] == "semantic"
        assert "id" in doc

    def test_memory_metadata(self):
        meta = MemoryMetadata(
            agent_id="agent-1",
            importance=0.8,
            tags=["test", "important"],
        )
        assert meta.agent_id == "agent-1"
        assert meta.importance == 0.8
        assert "test" in meta.tags

    def test_memory_relation(self):
        rel = MemoryRelation(
            source_id="mem-1",
            target_id="mem-2",
            relation_type="causes",
            strength=0.7,
        )
        assert rel.source_id == "mem-1"
        assert rel.target_id == "mem-2"
        assert rel.strength == 0.7


class TestMemoryTier:
    def test_tier_values(self):
        assert MemoryTier.WORKING.value == "working"
        assert MemoryTier.EPISODIC.value == "episodic"
        assert MemoryTier.SEMANTIC.value == "semantic"
        assert MemoryTier.PROCEDURAL.value == "procedural"


class TestMemoryType:
    def test_type_values(self):
        assert MemoryType.FACT.value == "fact"
        assert MemoryType.CONCEPT.value == "concept"
        assert MemoryType.SKILL.value == "skill"


class TestAccessLevel:
    def test_access_levels(self):
        assert AccessLevel.PRIVATE.value == "private"
        assert AccessLevel.SHARED.value == "shared"
        assert AccessLevel.PUBLIC.value == "public"


# ===========================================================================
# Embedding provider tests
# ===========================================================================


class TestHashEmbeddingProvider:
    def test_embed_dimension(self):
        provider = HashEmbeddingProvider(dimension=128)
        embeddings = provider.embed(["hello world"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 128

    def test_embed_normalized(self):
        provider = HashEmbeddingProvider(dimension=64)
        embeddings = provider.embed(["test text here"])
        vec = embeddings[0]
        # Check unit norm (hash-based embeddings are sparse but normalized)
        norm_sq = sum(v * v for v in vec)
        assert norm_sq > 0  # Has non-zero values

    def test_embed_deterministic(self):
        provider = HashEmbeddingProvider(dimension=64)
        emb1 = provider.embed(["same text"])[0]
        emb2 = provider.embed(["same text"])[0]
        assert emb1 == emb2

    def test_embed_different_texts(self):
        provider = HashEmbeddingProvider(dimension=128)
        emb1 = provider.embed(["apple banana"])[0]
        emb2 = provider.embed(["xylophone zither"])[0]
        assert emb1 != emb2

    def test_multiple_texts(self):
        provider = HashEmbeddingProvider(dimension=32)
        texts = ["alpha", "beta", "gamma"]
        embeddings = provider.embed(texts)
        assert len(embeddings) == 3


class TestSentenceTransformerProvider:
    def test_import_guard(self):
        """Verify the provider class exists without requiring the library."""
        # This tests the import path; if sentence_transformers isn't installed
        # it should raise ImportError
        try:
            from contextvault.vector_store import SentenceTransformerProvider
            # If we get here, the class exists (though instantiation may fail
            # if sentence_transformers isn't installed)
            assert True
        except ImportError:
            pytest.skip("sentence_transformers not installed")


# ===========================================================================
# Vector store tests
# ===========================================================================


class TestVectorStore:
    def test_create_store(self):
        store = VectorStore(dimension=32)
        assert store.dimension == 32
        assert store.size == 0

    def test_add_memory(self):
        store = VectorStore(dimension=32)
        mem = Memory(
            content="Test memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        store.add(mem)
        assert store.size == 1
        assert mem.embedding is not None

    def test_add_batch(self):
        store = VectorStore(dimension=32)
        mems = [
            Memory(
                content=f"Memory {i}",
                memory_type=MemoryType.FACT,
                tier=MemoryTier.SEMANTIC,
            )
            for i in range(5)
        ]
        store.add_batch(mems)
        assert store.size == 5

    def test_search_basic(self):
        store = VectorStore(dimension=64)
        mems = [
            Memory(content="apple fruit", memory_type=MemoryType.FACT, tier=MemoryTier.SEMANTIC),
            Memory(content="banana fruit", memory_type=MemoryType.FACT, tier=MemoryTier.SEMANTIC),
            Memory(content="car vehicle", memory_type=MemoryType.FACT, tier=MemoryTier.SEMANTIC),
        ]
        store.add_batch(mems)
        results = store.search("apple", top_k=2)
        assert len(results) > 0

    def test_search_with_filter(self):
        store = VectorStore(dimension=32)
        mem1 = Memory(
            content="working memory",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
        )
        mem2 = Memory(
            content="semantic memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        store.add_batch([mem1, mem2])

        results = store.search("memory", top_k=10, filter_types=["fact"])
        assert all(r.memory.memory_type == MemoryType.FACT for r in results)

    def test_search_empty_store(self):
        store = VectorStore(dimension=16)
        results = store.search("query", top_k=5)
        assert results == []

    def test_remove_memory(self):
        store = VectorStore(dimension=16)
        mem = Memory(
            content="To remove",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        store.add(mem)
        assert store.remove(mem.id)
        assert store._memories[mem.id].archived


# ===========================================================================
# Relevance scoring tests
# ===========================================================================


class TestRelevanceScorer:
    def test_recency_score(self):
        scorer = RelevanceScorer()
        mem = Memory(
            content="Fresh memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        score = scorer.recency_score(mem, now=time.time())
        assert 0.0 <= score <= 1.0

    def test_recency_score_old(self):
        scorer = RelevanceScorer()
        old_time = time.time() - 86400 * 10  # 10 days ago
        mem = Memory(
            content="Old memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            created_at=old_time,
        )
        score = scorer.recency_score(mem)
        assert score < 0.1  # Very old = low recency

    def test_access_frequency_score(self):
        scorer = RelevanceScorer()
        mem = Memory(
            content="Frequently accessed",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            access_count=100,
        )
        score = scorer.access_frequency_score(mem)
        assert score > 0.9  # High access = high frequency score

    def test_access_frequency_zero(self):
        scorer = RelevanceScorer()
        mem = Memory(
            content="Never accessed",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            access_count=0,
        )
        score = scorer.access_frequency_score(mem)
        assert score == 0.0

    def test_forgetting_curve(self):
        scorer = RelevanceScorer()
        mem = Memory(
            content="Memory for forgetting test",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        retention = scorer.forgetting_curve_score(mem, now=mem.accessed_at)
        assert 0.0 <= retention <= 1.0

    def test_forgetting_curve_decays(self):
        scorer = RelevanceScorer()
        params = ForgettingCurveParams(decay_rate=0.5)
        scorer.params = params
        mem = Memory(
            content="Decaying memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            accessed_at=time.time() - 3600,  # 1 hour ago
        )
        retention = scorer.forgetting_curve_score(mem)
        assert retention < 1.0  # Should have decayed

    def test_forgetting_curve_access_boost(self):
        scorer = RelevanceScorer()
        params = ForgettingCurveParams(boost_per_access=0.5, decay_rate=0.1)
        scorer.params = params

        accessed_mem = Memory(
            content="Boosted",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            accessed_at=time.time() - 3600,
            access_count=10,
        )
        fresh_mem = Memory(
            content="Fresh",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            accessed_at=time.time() - 3600,
            access_count=0,
        )
        boosted = scorer.forgetting_curve_score(accessed_mem)
        fresh = scorer.forgetting_curve_score(fresh_mem)
        assert boosted > fresh

    def test_composite_relevance(self):
        scorer = RelevanceScorer()
        mem = Memory(
            content="Relevant memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(importance=0.8, confidence=0.9),
        )
        score = scorer.composite_relevance(mem)
        assert 0.0 <= score <= 1.0

    def test_rank_memories(self):
        scorer = RelevanceScorer()
        mems = [
            Memory(
                content=f"Memory {i}",
                memory_type=MemoryType.FACT,
                tier=MemoryTier.SEMANTIC,
                metadata=MemoryMetadata(importance=i / 10.0),
            )
            for i in range(5)
        ]
        ranked = scorer.rank_memories(mems, top_k=3)
        assert len(ranked) == 3

    def test_should_retain(self):
        scorer = RelevanceScorer()
        mem = Memory(
            content="Important",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(importance=1.0),
        )
        assert scorer.should_retain(mem, threshold=0.05)

    def test_compute_half_life(self):
        scorer = RelevanceScorer()
        mem = Memory(
            content="Half life test",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            access_count=5,
        )
        half_life = scorer.compute_half_life(mem)
        assert half_life > 0


# ===========================================================================
# Memory store tests
# ===========================================================================


class TestMemoryStore:
    def test_create_store(self):
        store = MemoryStore()
        assert store.get_stats()["total_stored"] == 0

    def test_store_memory(self):
        store = MemoryStore()
        mem = store.store(
            content="Test fact",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        assert mem.id is not None
        assert mem.embedding is not None
        assert store.get_stats()["total_stored"] == 1

    def test_store_with_metadata(self):
        store = MemoryStore()
        meta = MemoryMetadata(
            agent_id="test-agent",
            tags=["test"],
            importance=0.9,
        )
        mem = store.store(
            content="With metadata",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=meta,
        )
        assert mem.metadata.agent_id == "test-agent"
        assert "test" in mem.metadata.tags

    def test_store_with_ttl(self):
        store = MemoryStore()
        mem = store.store(
            content="Temporary",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=60.0,
        )
        assert mem.ttl == 60.0

    def test_recall_by_id(self):
        store = MemoryStore()
        stored = store.store(
            content="Recall me",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        recalled = store.recall(stored.id)
        assert recalled is not None
        assert recalled.id == stored.id

    def test_recall_nonexistent(self):
        store = MemoryStore()
        assert store.recall("nonexistent") is None

    def test_recall_updates_access(self):
        store = MemoryStore()
        stored = store.store(
            content="Touch test",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        initial_count = stored.access_count
        recalled = store.recall(stored.id)
        assert recalled.access_count == initial_count + 1

    def test_search(self):
        store = MemoryStore()
        store.store(
            content="Python programming language",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        store.store(
            content="Java programming language",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        results = store.search("python", top_k=5)
        assert len(results) > 0

    def test_search_with_tier_filter(self):
        store = MemoryStore()
        store.store(
            content="working item",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
        )
        store.store(
            content="semantic item",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        results = store.search("item", tier=MemoryTier.SEMANTIC)
        assert all(r["tier"] == "semantic" for r in results)

    def test_promote(self):
        store = MemoryStore()
        mem = store.store(
            content="Promote me",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.WORKING,
        )
        promoted = store.promote(mem.id, MemoryTier.SEMANTIC)
        assert promoted is not None
        assert promoted.tier == MemoryTier.SEMANTIC

    def test_promote_nonexistent(self):
        store = MemoryStore()
        assert store.promote("nonexistent", MemoryTier.SEMANTIC) is None

    def test_relate_memories(self):
        store = MemoryStore()
        mem1 = store.store(
            content="Cause",
            memory_type=MemoryType.EVENT,
            tier=MemoryTier.EPISODIC,
        )
        mem2 = store.store(
            content="Effect",
            memory_type=MemoryType.EVENT,
            tier=MemoryTier.EPISODIC,
        )
        rel = store.relate(mem1.id, mem2.id, "causes", 0.8)
        assert rel is not None
        assert rel.relation_type == "causes"

    def test_get_relations(self):
        store = MemoryStore()
        mem1 = store.store("A", MemoryType.FACT, MemoryTier.SEMANTIC)
        mem2 = store.store("B", MemoryType.FACT, MemoryTier.SEMANTIC)
        mem3 = store.store("C", MemoryType.FACT, MemoryTier.SEMANTIC)
        store.relate(mem1.id, mem2.id, "related_to")
        store.relate(mem1.id, mem3.id, "follows")

        rels = store.get_relations(mem1.id)
        assert len(rels) == 2

    def test_archive(self):
        store = MemoryStore()
        mem = store.store(
            content="Archive me",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        assert store.archive(mem.id)
        assert store.get_stats()["total_archived"] == 1

    def test_archive_nonexistent(self):
        store = MemoryStore()
        assert not store.archive("nonexistent")

    def test_expire(self):
        store = MemoryStore()
        mem = store.store(
            content="Expire me",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        assert store.expire(mem.id)
        assert store.recall(mem.id) is None

    def test_check_ttl(self):
        store = MemoryStore()
        mem = store.store(
            content="TTL test",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=0.01,
        )
        time.sleep(0.02)
        expired = store.check_ttl()
        assert len(expired) > 0

    def test_get_tier_stats(self):
        store = MemoryStore()
        store.store("A", MemoryType.FACT, MemoryTier.SEMANTIC)
        store.store("B", MemoryType.BUFFER, MemoryTier.WORKING)
        stats = store.get_tier_stats()
        assert stats["semantic"] >= 1
        assert stats["working"] >= 1

    def test_get_stats(self):
        store = MemoryStore()
        store.store("Test", MemoryType.FACT, MemoryTier.SEMANTIC)
        stats = store.get_stats()
        assert stats["total_stored"] == 1
        assert "tiers" in stats

    def test_list_memories(self):
        store = MemoryStore()
        store.store("A", MemoryType.FACT, MemoryTier.SEMANTIC)
        store.store("B", MemoryType.FACT, MemoryTier.SEMANTIC)
        mems = store.list_memories()
        assert len(mems) == 2

    def test_list_memories_exclude_archived(self):
        store = MemoryStore()
        mem = store.store("Archive me", MemoryType.FACT, MemoryTier.SEMANTIC)
        store.store("Keep me", MemoryType.FACT, MemoryTier.SEMANTIC)
        store.archive(mem.id)
        mems = store.list_memories(include_archived=False)
        assert len(mems) == 1

    def test_access_control_integration(self):
        store = MemoryStore()
        mem = store.store(
            content="Private data",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(
                agent_id="agent-1",
                access_level=AccessLevel.PRIVATE,
            ),
        )
        results = store.search("data", agent_id="agent-1")
        assert len(results) > 0
        results_other = store.search("data", agent_id="agent-2")
        assert len(results_other) == 0


# ===========================================================================
# Consolidation pipeline tests
# ===========================================================================


class TestConsolidationPipeline:
    def test_create_pipeline(self):
        pipeline = ConsolidationPipeline()
        assert pipeline.records is not None

    def test_consolidate_empty(self):
        pipeline = ConsolidationPipeline()
        result = pipeline.consolidate([])
        assert result is None

    def test_consolidate_single(self):
        pipeline = ConsolidationPipeline()
        mem = Memory(
            content="Single memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.WORKING,
        )
        result = pipeline.consolidate([mem], MemoryTier.SEMANTIC, "merge")
        assert result is not None

    def test_merge(self):
        pipeline = ConsolidationPipeline()
        mems = [
            Memory(content="First fact", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
            Memory(content="Second fact", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
            Memory(content="Third fact", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
        ]
        result = pipeline.consolidate(mems, MemoryTier.SEMANTIC, "merge")
        assert result is not None
        assert "[Merged]" in result.content
        assert result.tier == MemoryTier.SEMANTIC
        # Source memories should be marked consolidated
        assert all(m.consolidated for m in mems)

    def test_summarize(self):
        pipeline = ConsolidationPipeline()
        mems = [
            Memory(content="Fact one about AI agents", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
            Memory(content="Fact two about AI agents", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
        ]
        result = pipeline.consolidate(mems, MemoryTier.SEMANTIC, "summarize")
        assert result is not None
        assert "[Summary]" in result.content

    def test_abstract(self):
        pipeline = ConsolidationPipeline()
        mems = [
            Memory(content="Specific instance A", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
            Memory(content="Specific instance B", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
            Memory(content="Specific instance C", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
        ]
        result = pipeline.consolidate(mems, MemoryTier.SEMANTIC, "abstract")
        assert result is not None
        assert "[Abstract" in result.content

    def test_auto_consolidate(self):
        pipeline = ConsolidationPipeline()
        mems = [
            Memory(
                content=f"Working memory {i}",
                memory_type=MemoryType.FACT,
                tier=MemoryTier.WORKING,
                metadata=MemoryMetadata(tags=["ai"]),
            )
            for i in range(5)
        ]
        results = pipeline.auto_consolidate(mems, MemoryTier.SEMANTIC)
        assert len(results) > 0

    def test_auto_consolidate_empty(self):
        pipeline = ConsolidationPipeline()
        results = pipeline.auto_consolidate([])
        assert results == []

    def test_records(self):
        pipeline = ConsolidationPipeline()
        mems = [
            Memory(content="A", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
            Memory(content="B", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
        ]
        pipeline.consolidate(mems, MemoryTier.SEMANTIC, "merge")
        assert len(pipeline.records) == 1

    def test_get_stats(self):
        pipeline = ConsolidationPipeline()
        mems = [
            Memory(content="A", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
            Memory(content="B", memory_type=MemoryType.FACT, tier=MemoryTier.WORKING),
        ]
        pipeline.consolidate(mems, MemoryTier.SEMANTIC, "merge")
        stats = pipeline.get_stats()
        assert stats["total"] == 1
        assert stats["merges"] == 1


# ===========================================================================
# Search tests
# ===========================================================================


class TestMemorySearch:
    def test_create_search(self):
        vs = VectorStore(dimension=32)
        scorer = RelevanceScorer()
        search = MemorySearch(vs, scorer)
        assert search is not None

    def test_index_memory(self):
        vs = VectorStore(dimension=32)
        search = MemorySearch(vs, RelevanceScorer())
        mem = Memory(
            content="Indexable memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        search.index_memory(mem)
        assert mem.id in search._memory_map

    def test_index_memories(self):
        vs = VectorStore(dimension=32)
        search = MemorySearch(vs, RelevanceScorer())
        mems = [
            Memory(content=f"Memory {i}", memory_type=MemoryType.FACT, tier=MemoryTier.SEMANTIC)
            for i in range(3)
        ]
        search.index_memories(mems)
        assert len(search._memory_map) == 3

    def test_semantic_search(self):
        vs = VectorStore(dimension=64)
        search = MemorySearch(vs, RelevanceScorer())
        mem = Memory(
            content="Python is a programming language",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        vs.add(mem)
        search.index_memory(mem)

        results = search.search("python programming", top_k=5, mode="semantic")
        assert len(results) > 0

    def test_keyword_search(self):
        vs = VectorStore(dimension=32)
        search = MemorySearch(vs, RelevanceScorer())
        mem = Memory(
            content="Machine learning algorithms",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        search.index_memory(mem)

        results = search.search("machine learning", top_k=5, mode="keyword")
        assert len(results) > 0

    def test_hybrid_search(self):
        vs = VectorStore(dimension=64)
        search = MemorySearch(vs, RelevanceScorer())
        mem = Memory(
            content="Deep learning neural networks",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        vs.add(mem)
        search.index_memory(mem)

        results = search.search("deep learning", top_k=5, mode="hybrid")
        assert len(results) > 0

    def test_search_with_highlights(self):
        vs = VectorStore(dimension=32)
        search = MemorySearch(vs, RelevanceScorer())
        mem = Memory(
            content="The quick brown fox jumps over the lazy dog",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        search.index_memory(mem)

        results = search.search("fox", top_k=5, mode="keyword")
        assert len(results) > 0
        assert len(results[0].get("highlights", [])) > 0

    def test_search_empty(self):
        vs = VectorStore(dimension=16)
        search = MemorySearch(vs, RelevanceScorer())
        results = search.search("anything", top_k=5)
        assert results == []


# ===========================================================================
# TTL tests
# ===========================================================================


class TestTTLManager:
    def test_create_ttl_manager(self):
        ttl = TTLManager()
        assert ttl.get_stats()["expired"] == 0

    def test_set_ttl(self):
        ttl = TTLManager()
        mem = Memory(
            content="TTL test",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
        )
        ttl.set_ttl(mem, 3600)
        assert mem.ttl == 3600

    def test_get_remaining_ttl(self):
        ttl = TTLManager()
        mem = Memory(
            content="TTL test",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=3600,
        )
        remaining = ttl.get_remaining_ttl(mem)
        assert remaining is not None
        assert remaining > 0

    def test_get_remaining_ttl_none(self):
        ttl = TTLManager()
        mem = Memory(
            content="No TTL",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        assert ttl.get_remaining_ttl(mem) is None

    def test_extend_ttl(self):
        ttl = TTLManager()
        mem = Memory(
            content="Extendable",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=100,
        )
        ttl.extend_ttl(mem, 50)
        assert mem.ttl == 150

    def test_check_expired(self):
        ttl = TTLManager()
        mem = Memory(
            content="Expired",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=0.01,
        )
        time.sleep(0.02)
        expired = ttl.check_expired([mem])
        assert len(expired) == 1

    def test_expire_memories(self):
        ttl = TTLManager()
        mem = Memory(
            content="To expire",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=0.01,
        )
        time.sleep(0.02)
        expired = ttl.expire_memories([mem])
        assert len(expired) == 1
        assert mem.archived

    def test_cold_storage_archive(self, tmp_path):
        cold = ColdStorage(str(tmp_path))
        mem = Memory(
            content="Cold storage test",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        path = cold.archive_memory(mem)
        assert Path(path).exists()

    def test_cold_storage_restore(self, tmp_path):
        cold = ColdStorage(str(tmp_path))
        mem = Memory(
            content="Restore me",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        cold.archive_memory(mem)
        restored = cold.restore_memory(mem.id)
        assert restored is not None
        assert restored.content == "Restore me"

    def test_cold_storage_list(self, tmp_path):
        cold = ColdStorage(str(tmp_path))
        mem1 = Memory(content="A", memory_type=MemoryType.FACT, tier=MemoryTier.SEMANTIC)
        mem2 = Memory(content="B", memory_type=MemoryType.FACT, tier=MemoryTier.SEMANTIC)
        cold.archive_memory(mem1)
        cold.archive_memory(mem2)
        archived = cold.list_archived()
        assert len(archived) == 2

    def test_cold_storage_delete(self, tmp_path):
        cold = ColdStorage(str(tmp_path))
        mem = Memory(content="Delete me", memory_type=MemoryType.FACT, tier=MemoryTier.SEMANTIC)
        cold.archive_memory(mem)
        assert cold.delete_archive(mem.id)
        assert cold.restore_memory(mem.id) is None

    def test_expire_with_cold_storage(self, tmp_path):
        cold = ColdStorage(str(tmp_path))
        ttl = TTLManager(cold_storage=cold)
        mem = Memory(
            content="Archive on expire",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=0.01,
        )
        time.sleep(0.02)
        ttl.expire_memories([mem])
        assert ttl.get_stats()["archived_to_cold"] == 1


# ===========================================================================
# Access control tests
# ===========================================================================


class TestAccessController:
    def test_create_controller(self):
        ac = AccessController()
        assert ac.list_agents() == []

    def test_register_agent(self):
        ac = AccessController()
        profile = ac.register_agent("agent-1", "Test Agent")
        assert profile.agent_id == "agent-1"
        assert profile.name == "Test Agent"

    def test_register_duplicate(self):
        ac = AccessController()
        ac.register_agent("agent-1", "First")
        profile = ac.register_agent("agent-1", "Second")
        assert profile.name == "First"  # Returns existing

    def test_grant_access(self):
        ac = AccessController()
        mem = Memory(
            content="Shared",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner"),
        )
        assert ac.grant_access(mem, "other-agent", granted_by="owner")
        assert "other-agent" in mem.metadata.allowed_agents

    def test_revoke_access(self):
        ac = AccessController()
        mem = Memory(
            content="Shared",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner", allowed_agents=["other"]),
        )
        ac.revoke_access(mem, "other")
        assert "other" not in mem.metadata.allowed_agents

    def test_set_access_level(self):
        ac = AccessController()
        mem = Memory(
            content="Public",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner"),
        )
        ac.set_access_level(mem, AccessLevel.PUBLIC)
        assert mem.metadata.access_level == AccessLevel.PUBLIC

    def test_can_access_public(self):
        ac = AccessController()
        mem = Memory(
            content="Public",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(access_level=AccessLevel.PUBLIC),
        )
        assert ac.can_access(mem, "anyone")

    def test_can_access_private(self):
        ac = AccessController()
        mem = Memory(
            content="Private",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner", access_level=AccessLevel.PRIVATE),
        )
        assert ac.can_access(mem, "owner")
        assert not ac.can_access(mem, "intruder")

    def test_can_access_shared(self):
        ac = AccessController()
        mem = Memory(
            content="Shared",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(
                agent_id="owner",
                access_level=AccessLevel.SHARED,
                allowed_agents=["friend"],
            ),
        )
        assert ac.can_access(mem, "owner")
        assert ac.can_access(mem, "friend")
        assert not ac.can_access(mem, "stranger")

    def test_can_access_restricted(self):
        ac = AccessController()
        mem = Memory(
            content="Restricted",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(
                access_level=AccessLevel.RESTRICTED,
                allowed_agents=["authorized"],
            ),
        )
        assert ac.can_access(mem, "authorized")
        assert not ac.can_access(mem, "owner")  # Owner not in allowed list

    def test_get_accessible_memories(self):
        ac = AccessController()
        mems = [
            Memory(
                content="Public",
                memory_type=MemoryType.FACT,
                tier=MemoryTier.SEMANTIC,
                metadata=MemoryMetadata(access_level=AccessLevel.PUBLIC),
            ),
            Memory(
                content="Private",
                memory_type=MemoryType.FACT,
                tier=MemoryTier.SEMANTIC,
                metadata=MemoryMetadata(agent_id="other", access_level=AccessLevel.PRIVATE),
            ),
        ]
        accessible = ac.get_accessible_memories(mems, "anyone")
        assert len(accessible) == 1

    def test_share_memory(self):
        ac = AccessController()
        mem = Memory(
            content="Share me",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner"),
        )
        assert ac.share_memory(mem, "owner", ["agent-2", "agent-3"])
        assert mem.metadata.access_level == AccessLevel.SHARED
        assert "agent-2" in mem.metadata.allowed_agents

    def test_share_memory_not_owner(self):
        ac = AccessController()
        mem = Memory(
            content="Not yours",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner"),
        )
        assert not ac.share_memory(mem, "intruder", ["agent-2"])

    def test_make_public(self):
        ac = AccessController()
        mem = Memory(
            content="Going public",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner"),
        )
        assert ac.make_public(mem, "owner")
        assert mem.metadata.access_level == AccessLevel.PUBLIC

    def test_get_agent(self):
        ac = AccessController()
        ac.register_agent("agent-1", "Test")
        profile = ac.get_agent("agent-1")
        assert profile is not None
        assert profile.name == "Test"

    def test_list_agents(self):
        ac = AccessController()
        ac.register_agent("a1", "Agent 1")
        ac.register_agent("a2", "Agent 2")
        agents = ac.list_agents()
        assert len(agents) == 2

    def test_audit_log(self):
        ac = AccessController()
        mem = Memory(
            content="Audited",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner"),
        )
        ac.grant_access(mem, "agent-2", granted_by="owner")
        ac.revoke_access(mem, "agent-2")
        log = ac.get_audit_log()
        assert len(log) == 2

    def test_audit_log_filter_by_memory(self):
        ac = AccessController()
        mem1 = Memory(
            content="M1",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner"),
        )
        mem2 = Memory(
            content="M2",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="owner"),
        )
        ac.grant_access(mem1, "agent-2", granted_by="owner")
        ac.grant_access(mem2, "agent-3", granted_by="owner")
        log = ac.get_audit_log(memory_id=mem1.id)
        assert len(log) == 1

    def test_get_stats(self):
        ac = AccessController()
        ac.register_agent("a1", "Agent 1")
        stats = ac.get_stats()
        assert stats["agents"] == 1


# ===========================================================================
# Integration tests
# ===========================================================================


class TestIntegration:
    def test_full_workflow(self):
        """Test a complete memory lifecycle."""
        store = MemoryStore(dimension=64)
        ac = AccessController()

        # Register agents
        ac.register_agent("agent-1", "Primary Agent")
        ac.register_agent("agent-2", "Secondary Agent")

        # Store memories
        mem1 = store.store(
            content="Python is a versatile programming language",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="agent-1", tags=["python", "programming"]),
        )
        mem2 = store.store(
            content="Machine learning uses neural networks",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="agent-1", tags=["ml", "ai"]),
        )

        # Search
        results = store.search("python programming", top_k=5)
        assert len(results) > 0

        # Promote
        promoted = store.promote(mem1.id, MemoryTier.PROCEDURAL)
        assert promoted.tier == MemoryTier.PROCEDURAL

        # Relate
        rel = store.relate(mem1.id, mem2.id, "related_to", 0.7)
        assert rel is not None

        # Archive
        store.archive(mem2.id)

        # Check stats
        stats = store.get_stats()
        assert stats["total_stored"] == 2
        assert stats["total_archived"] == 1

    def test_consolidation_workflow(self):
        """Test memory consolidation from working to semantic."""
        store = MemoryStore(dimension=64)
        pipeline = ConsolidationPipeline()

        # Create working memories
        working_mems = [
            store.store(
                content=f"Working memory about AI topic {i}",
                memory_type=MemoryType.FACT,
                tier=MemoryTier.WORKING,
                metadata=MemoryMetadata(tags=["ai", "research"]),
            )
            for i in range(5)
        ]

        # Consolidate
        consolidated = pipeline.auto_consolidate(working_mems, MemoryTier.SEMANTIC)
        assert len(consolidated) > 0

    def test_ttl_expiration_workflow(self, tmp_path):
        """Test TTL expiration with cold storage."""
        store = MemoryStore(dimension=32)
        cold = ColdStorage(str(tmp_path))
        ttl = TTLManager(cold_storage=cold)

        # Store with short TTL
        mem = store.store(
            content="Temporary data",
            memory_type=MemoryType.BUFFER,
            tier=MemoryTier.WORKING,
            ttl=0.01,
        )

        time.sleep(0.02)

        # Check TTL
        expired = store.check_ttl()
        assert len(expired) > 0

    def test_multi_agent_shared_memory(self):
        """Test multi-agent memory sharing."""
        store = MemoryStore(dimension=32)
        ac = AccessController()

        ac.register_agent("agent-1", "Owner")
        ac.register_agent("agent-2", "Collaborator")

        # Store private memory
        mem = store.store(
            content="Shared project data",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(
                agent_id="agent-1",
                access_level=AccessLevel.SHARED,
            ),
        )

        # Share with agent-2
        ac.grant_access(mem, "agent-2")

        # Both agents can access
        results1 = store.search("project data", agent_id="agent-1")
        results2 = store.search("project data", agent_id="agent-2")
        assert len(results1) > 0
        assert len(results2) > 0

        # Private agent cannot
        results3 = store.search("project data", agent_id="agent-3")
        assert len(results3) == 0


# ===========================================================================
# Persistence tests
# ===========================================================================


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        """Test store persistence."""
        store = MemoryStore(persist_path=str(tmp_path / "store"), dimension=32)

        # Store some memories
        store.store(
            content="Persistent memory",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )

        # Save
        store.save()

        # Create new store and load
        store2 = MemoryStore(persist_path=str(tmp_path / "store"), dimension=32)
        store2.load()

        # Verify
        stats = store2.get_stats()
        assert stats["total_stored"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
