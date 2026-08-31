#!/usr/bin/env python3
"""
RAG Engine Plugin — Retrieval Augmented Generation
=================================================
Features:
- Document chunking and embedding
- Vector storage (TF-IDF based, no external deps)
- Semantic search with relevance scoring
- Multi-source retrieval
- Context building for LLM prompts
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("hermes_rag_engine")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: list[str] = field(default_factory=list)
        shell_commands: list[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: list[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: list[str] = field(default_factory=list)
        path: Path | None = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


@dataclass
class Chunk:
    """A document chunk."""
    id: str
    source: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class SearchResult:
    """A search result."""
    chunk: Chunk
    score: float
    matches: list[str] = field(default_factory=list)


class DocumentChunker:
    """Split documents into chunks."""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, source: str = "unknown") -> list[Chunk]:
        """Chunk text into overlapping segments."""
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks: list[Chunk] = []
        current_chunk = []
        current_size = 0
        chunk_idx = 0
        
        for para in paragraphs:
            para_words = para.split()
            
            if current_size + len(para_words) > self.chunk_size and current_chunk:
                # Finalize current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append(Chunk(
                    id=f"{source}_{chunk_idx}",
                    source=source,
                    text=chunk_text,
                    metadata={"chunk_idx": chunk_idx},
                ))
                chunk_idx += 1
                
                # Keep overlap
                overlap_words = current_chunk[-self.overlap:] if self.overlap < len(current_chunk) else current_chunk
                current_chunk = overlap_words
                current_size = len(overlap_words)
            
            current_chunk.extend(para_words)
            current_size += len(para_words)
        
        # Final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(Chunk(
                id=f"{source}_{chunk_idx}",
                source=source,
                text=chunk_text,
                metadata={"chunk_idx": chunk_idx},
            ))
        
        return chunks


class TFIDFEmbedder:
    """Simple TF-IDF based embedding."""
    
    def __init__(self):
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.doc_count = 0
    
    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text."""
        text = text.lower()
        words = re.findall(r'\b[a-z0-9_]+\b', text)
        return [w for w in words if len(w) > 1]
    
    def fit(self, documents: list[str]):
        """Fit the embedder on a corpus."""
        self.doc_count = len(documents)
        doc_freq: dict[str, int] = {}
        
        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1
        
        # Build vocab and IDF
        self.vocab = {token: idx for idx, token in enumerate(sorted(doc_freq.keys()))}
        for token, freq in doc_freq.items():
            self.idf[token] = math.log((self.doc_count + 1) / (freq + 1)) + 1
    
    def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        if not self.vocab:
            return []
        
        tokens = self._tokenize(text)
        token_counts = Counter(tokens)
        
        vector = [0.0] * len(self.vocab)
        for token, count in token_counts.items():
            if token in self.vocab:
                idx = self.vocab[token]
                tf = count / len(tokens) if tokens else 0
                vector[idx] = tf * self.idf.get(token, 0)
        
        # Normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Cosine similarity."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)


class RAGEngine:
    """Retrieval Augmented Generation engine."""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunker = DocumentChunker(chunk_size, overlap)
        self.embedder = TFIDFEmbedder()
        self.chunks: dict[str, Chunk] = {}
        self.fitted = False
    
    def add_document(self, text: str, source: str = "unknown", metadata: dict | None = None) -> int:
        """Add a document to the index."""
        chunks = self.chunker.chunk_text(text, source)
        
        # Add metadata
        for chunk in chunks:
            if metadata:
                chunk.metadata.update(metadata)
            self.chunks[chunk.id] = chunk
        
        # Re-fit embedder
        self._refit()
        
        return len(chunks)
    
    def add_documents(self, documents: list[dict[str, Any]]) -> int:
        """Add multiple documents."""
        total = 0
        for doc in documents:
            text = doc.get("text", "")
            source = doc.get("source", "unknown")
            metadata = doc.get("metadata", {})
            total += self.add_document(text, source, metadata)
        return total
    
    def _refit(self):
        """Re-fit the embedder on all chunk texts."""
        texts = [chunk.text for chunk in self.chunks.values()]
        if texts:
            self.embedder.fit(texts)
            for chunk in self.chunks.values():
                chunk.embedding = self.embedder.embed(chunk.text)
            self.fitted = True
    
    def search(self, query: str, top_k: int = 5, threshold: float = 0.0) -> list[SearchResult]:
        """Search for relevant chunks."""
        if not self.fitted:
            return []
        
        query_embedding = self.embedder.embed(query)
        if not query_embedding:
            return []
        
        results: list[SearchResult] = []
        
        for chunk in self.chunks.values():
            if not chunk.embedding:
                continue
            
            score = self.embedder.similarity(query_embedding, chunk.embedding)
            
            # Also do keyword matching
            query_tokens = set(self.embedder._tokenize(query))
            chunk_tokens = set(self.embedder._tokenize(chunk.text))
            keyword_overlap = len(query_tokens.intersection(chunk_tokens))
            
            # Combine scores
            combined_score = score * 0.7 + (keyword_overlap / max(len(query_tokens), 1)) * 0.3
            
            if combined_score >= threshold:
                matches = list(query_tokens.intersection(chunk_tokens))
                results.append(SearchResult(chunk=chunk, score=combined_score, matches=matches))
        
        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        
        return results[:top_k]
    
    def build_context(self, query: str, top_k: int = 3, max_chars: int = 2000) -> str:
        """Build a context string for LLM prompts."""
        results = self.search(query, top_k=top_k)
        
        context_parts = []
        total_chars = 0
        
        for i, result in enumerate(results, 1):
            chunk_text = result.chunk.text
            if total_chars + len(chunk_text) > max_chars:
                chunk_text = chunk_text[:max_chars - total_chars]
            
            context_parts.append(f"[Source {i}: {result.chunk.source}]\n{chunk_text}")
            total_chars += len(chunk_text)
            
            if total_chars >= max_chars:
                break
        
        return "\n\n".join(context_parts)
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the index."""
        sources: dict[str, int] = {}
        for chunk in self.chunks.values():
            sources[chunk.source] = sources.get(chunk.source, 0) + 1
        
        return {
            "total_chunks": len(self.chunks),
            "total_sources": len(sources),
            "sources": sources,
            "fitted": self.fitted,
            "vocab_size": len(self.embedder.vocab),
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """RAG Engine Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="rag_engine",
            version="1.0.0",
            description="Retrieval Augmented Generation with TF-IDF embeddings, semantic search, and context building",
            license="MIT",
            source="internal",
            capabilities=["document_indexing", "semantic_search", "context_building", "rag_retrieval"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.engine: RAGEngine | None = None
    
    async def load(self) -> bool:
        self.engine = RAGEngine()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.engine:
            self.engine = RAGEngine()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.engine is not None,
            "chunks": len(self.engine.chunks) if self.engine else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def add_document(self, text: str, source: str = "unknown", metadata: dict | None = None) -> int:
        return self.engine.add_document(text, source, metadata)
    
    def add_documents(self, documents: list[dict[str, Any]]) -> int:
        return self.engine.add_documents(documents)
    
    def search(self, query: str, top_k: int = 5, threshold: float = 0.0) -> list[dict[str, Any]]:
        results = self.engine.search(query, top_k, threshold)
        return [
            {
                "source": r.chunk.source,
                "text": r.chunk.text,
                "score": r.score,
                "matches": r.matches,
                "metadata": r.chunk.metadata,
            }
            for r in results
        ]
    
    def build_context(self, query: str, top_k: int = 3, max_chars: int = 2000) -> str:
        return self.engine.build_context(query, top_k, max_chars)
    
    def get_stats(self) -> dict[str, Any]:
        return self.engine.get_stats()
    
    def get_capabilities(self) -> list[str]:
        return self.manifest.capabilities
