"""ContextVault — Agent Long-Term Memory Store."""

__version__ = "1.0.0"

from contextvault.access_control import AccessController
from contextvault.consolidation import ConsolidationPipeline
from contextvault.dashboard import MemoryDashboard
from contextvault.k8s_operator import (
    ContextVaultOperator,
    ContextVaultSpec,
    KubernetesManifestGenerator,
    ScalingPolicy,
)
from contextvault.memory_store import MemoryStore
from contextvault.models import (
    Memory,
    MemoryMetadata,
    MemoryRelation,
    MemoryTier,
    MemoryType,
    SearchResult,
)
from contextvault.relevance import ForgettingCurveParams, RelevanceScorer
from contextvault.search import MemorySearch
from contextvault.ttl import ColdStorage, TTLManager
from contextvault.vector_store import (
    EmbeddingProvider,
    HashEmbeddingProvider,
    VectorStore,
)

__all__ = [
    "AccessController",
    "ColdStorage",
    "ConsolidationPipeline",
    "ContextVaultOperator",
    "ContextVaultSpec",
    "EmbeddingProvider",
    "ForgettingCurveParams",
    "HashEmbeddingProvider",
    "KubernetesManifestGenerator",
    "Memory",
    "MemoryDashboard",
    "MemoryMetadata",
    "MemoryRelation",
    "MemorySearch",
    "MemoryStore",
    "MemoryTier",
    "MemoryType",
    "RelevanceScorer",
    "ScalingPolicy",
    "SearchResult",
    "TTLManager",
    "VectorStore",
]
