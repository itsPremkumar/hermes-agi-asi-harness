#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v6.0 — RAG ENGINE
==========================================
Memory-augmented generation with semantic search.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_rag")


@dataclass
class IndexedDocument:
    """An indexed document."""
    doc_id: str
    content: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class RAGEngine:
    """Memory-augmented generation engine."""
    
    def __init__(self, index_path: str = "state/memory/rag_index.json"):
        self.index_path = index_path
        self._documents: dict[str, IndexedDocument] = {}
        self._knowledge_graph: dict[str, list[str]] = {}
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        self._load()
    
    def _load(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r') as f:
                    data = json.load(f)
                    for doc_data in data.get("documents", []):
                        doc = IndexedDocument(**doc_data)
                        self._documents[doc.doc_id] = doc
            except Exception as e:
                logger.warning("Failed to load RAG index: %s", e)
    
    def save(self):
        with open(self.index_path, 'w') as f:
            json.dump({
                "documents": [doc.__dict__ for doc in self._documents.values()]
            }, f, indent=2, default=str)
    
    def index(self, content: str, source: str = "memory", metadata: dict[str, Any] | None = None) -> str:
        """Index a document."""
        doc_id = str(uuid.uuid4())
        doc = IndexedDocument(
            doc_id=doc_id,
            content=content,
            source=source,
            metadata=metadata or {},
            embedding=self._embed(content)
        )
        self._documents[doc_id] = doc
        self.save()
        return doc_id
    
    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Semantic search."""
        query_emb = self._embed(query)
        scored = []
        
        for doc in self._documents.values():
            score = self._cosine(query_emb, doc.embedding)
            scored.append((score, doc))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {
                "doc_id": doc.doc_id,
                "content": doc.content[:200],
                "score": score,
                "source": doc.source
            }
            for score, doc in scored[:limit]
        ]
    
    def hybrid_search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Hybrid search: keyword + semantic."""
        keyword_results = self._keyword_search(query, limit)
        semantic_results = self.search(query, limit)
        
        # Merge and deduplicate
        seen = set()
        merged = []
        for result in keyword_results + semantic_results:
            if result["doc_id"] not in seen:
                seen.add(result["doc_id"])
                merged.append(result)
        
        return merged[:limit]
    
    def _keyword_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Keyword search."""
        query_lower = query.lower()
        results = []
        
        for doc in self._documents.values():
            if query_lower in doc.content.lower():
                results.append({
                    "doc_id": doc.doc_id,
                    "content": doc.content[:200],
                    "score": 0.5,
                    "source": doc.source
                })
        
        return results[:limit]
    
    def _embed(self, text: str) -> dict[str, float]:
        """Simple token-based embedding."""
        vec = {}
        for token in re.findall(r'[a-z0-9_]+', text.lower()):
            if len(token) >= 3:
                vec[token] = vec.get(token, 0.0) + 1.0
        
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {k: v / norm for k, v in vec.items()}
    
    def _cosine(self, a: dict[str, float], b: dict[str, float]) -> float:
        """Cosine similarity."""
        if not a or not b:
            return 0.0
        return sum(a[k] * b[k] for k in (set(a) & set(b)))
    
    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "documents": len(self._documents)}
