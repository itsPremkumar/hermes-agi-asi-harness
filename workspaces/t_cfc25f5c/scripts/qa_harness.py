"""QA harness for ContextVault — automated quality checks."""

from __future__ import annotations

import importlib
import sys
import traceback
from typing import List, Tuple


def check_imports() -> Tuple[bool, str]:
    """Verify all core modules can be imported."""
    modules = [
        "contextvault",
        "contextvault.models",
        "contextvault.memory_store",
        "contextvault.vector_store",
        "contextvault.consolidation",
        "contextvault.relevance",
        "contextvault.search",
        "contextvault.ttl",
        "contextvault.access_control",
        "contextvault.cli",
        "contextvault.server",
        "contextvault.k8s_operator",
        "contextvault.dashboard",
    ]

    failed = []
    for mod in modules:
        try:
            importlib.import_module(mod)
        except Exception as e:
            failed.append(f"{mod}: {e}")

    if failed:
        return False, f"Import failures: {', '.join(failed)}"
    return True, f"All {len(modules)} modules imported successfully"


def check_public_api() -> Tuple[bool, str]:
    """Verify the public API surface is accessible."""
    try:
        from contextvault import (
            AccessController,
            ColdStorage,
            ConsolidationPipeline,
            ContextVaultOperator,
            ContextVaultSpec,
            EmbeddingProvider,
            ForgettingCurveParams,
            HashEmbeddingProvider,
            KubernetesManifestGenerator,
            Memory,
            MemoryDashboard,
            MemoryMetadata,
            MemoryRelation,
            MemorySearch,
            MemoryStore,
            MemoryTier,
            MemoryType,
            RelevanceScorer,
            ScalingPolicy,
            SearchResult,
            TTLManager,
            VectorStore,
        )

        # Instantiate key classes
        store = MemoryStore()
        assert store is not None

        ac = AccessController()
        assert ac is not None

        pipeline = ConsolidationPipeline()
        assert pipeline is not None

        scorer = RelevanceScorer()
        assert scorer is not None

        vs = VectorStore()
        assert vs is not None

        return True, "All public API classes instantiable"
    except Exception as e:
        return False, f"Public API check failed: {e}\n{traceback.format_exc()}"


def check_models() -> Tuple[bool, str]:
    """Verify core data models work correctly."""
    try:
        from contextvault.models import (
            AccessLevel,
            Memory,
            MemoryMetadata,
            MemoryRelation,
            MemoryTier,
            MemoryType,
        )

        # Create memory
        mem = Memory(
            content="Test",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
        )
        assert mem.id is not None
        assert mem.content == "Test"
        assert mem.content_hash is not None

        # Test metadata
        meta = MemoryMetadata(agent_id="test", importance=0.5, tags=["test"])
        assert meta.agent_id == "test"

        # Test relation
        rel = MemoryRelation(source_id="a", target_id="b", relation_type="causes")
        assert rel.source_id == "a"

        return True, "All models functional"
    except Exception as e:
        return False, f"Models check failed: {e}\n{traceback.format_exc()}"


def check_store_operations() -> Tuple[bool, str]:
    """Verify MemoryStore operations work."""
    try:
        from contextvault.memory_store import MemoryStore
        from contextvault.models import MemoryMetadata, MemoryTier, MemoryType

        store = MemoryStore()

        # Store
        mem = store.store("Test content", MemoryType.FACT, MemoryTier.SEMANTIC)
        assert mem.id is not None

        # Recall
        recalled = store.recall(mem.id)
        assert recalled is not None
        assert recalled.content == "Test content"

        # Search
        results = store.search("test", top_k=5)
        assert len(results) > 0

        # Stats
        stats = store.get_stats()
        assert stats["total_stored"] == 1

        return True, "MemoryStore operations working"
    except Exception as e:
        return False, f"Store operations check failed: {e}\n{traceback.format_exc()}"


def check_access_control() -> Tuple[bool, str]:
    """Verify AccessController works."""
    try:
        from contextvault.access_control import AccessController
        from contextvault.models import MemoryMetadata, MemoryType, MemoryTier, AccessLevel

        ac = AccessController()
        ac.register_agent("agent-1", "Test")

        from contextvault.models import Memory
        mem = Memory(
            content="Test",
            memory_type=MemoryType.FACT,
            tier=MemoryTier.SEMANTIC,
            metadata=MemoryMetadata(agent_id="agent-1", access_level=AccessLevel.PRIVATE),
        )

        assert ac.can_access(mem, "agent-1")
        assert not ac.can_access(mem, "agent-2")

        ac.grant_access(mem, "agent-2", granted_by="agent-1")
        assert ac.can_access(mem, "agent-2")

        return True, "Access control working"
    except Exception as e:
        return False, f"Access control check failed: {e}\n{traceback.format_exc()}"


def check_k8s_operator() -> Tuple[bool, str]:
    """Verify Kubernetes operator works."""
    try:
        from contextvault.k8s_operator import (
            ContextVaultOperator,
            ContextVaultSpec,
            KubernetesManifestGenerator,
            ScalingPolicy,
        )

        spec = ContextVaultSpec(name="test")
        gen = KubernetesManifestGenerator(spec)
        manifests = gen.generate_all()
        assert "deployment" in manifests
        assert "service" in manifests
        assert "hpa" in manifests

        op = ContextVaultOperator()
        op.create_deployment(spec)
        assert op.get_deployment("test") is not None
        assert len(op.list_deployments()) == 1

        return True, "Kubernetes operator working"
    except Exception as e:
        return False, f"Kubernetes operator check failed: {e}\n{traceback.format_exc()}"


def check_dashboard() -> Tuple[bool, str]:
    """Verify dashboard works."""
    try:
        from contextvault.dashboard import MemoryDashboard, format_dashboard_text
        from contextvault.memory_store import MemoryStore
        from contextvault.models import MemoryType, MemoryTier

        store = MemoryStore()
        store.store("Test memory", MemoryType.FACT, MemoryTier.SEMANTIC)

        dash = MemoryDashboard(store)
        report = dash.full_report()
        assert "stats" in report
        assert "tier_distribution" in report

        text = format_dashboard_text(report)
        assert len(text) > 0

        return True, "Dashboard working"
    except Exception as e:
        return False, f"Dashboard check failed: {e}\n{traceback.format_exc()}"


def run_qa() -> bool:
    """Run all QA checks. Returns True if all pass."""
    checks: List[Tuple[str, callable]] = [
        ("Imports", check_imports),
        ("Public API", check_public_api),
        ("Models", check_models),
        ("Store Operations", check_store_operations),
        ("Access Control", check_access_control),
        ("Kubernetes Operator", check_k8s_operator),
        ("Dashboard", check_dashboard),
    ]

    print("=" * 60)
    print(" ContextVault QA Harness")
    print("=" * 60)

    all_passed = True
    results = []

    for name, check_fn in checks:
        passed, message = check_fn()
        status = "PASS" if passed else "FAIL"
        symbol = "[✓]" if passed else "[✗]"
        print(f"  {symbol} {name}: {status} — {message}")
        if not passed:
            all_passed = False
        results.append((name, passed, message))

    print("=" * 60)

    if all_passed:
        print(f" All {len(checks)} QA checks passed!")
    else:
        failed = sum(1 for _, p, _ in results if not p)
        print(f" {failed}/{len(checks)} checks failed")

    print("=" * 60)
    return all_passed


if __name__ == "__main__":
    success = run_qa()
    sys.exit(0 if success else 1)
