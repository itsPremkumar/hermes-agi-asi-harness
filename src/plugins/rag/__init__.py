#!/usr/bin/env python3
"""RAG engine plugin."""

from core.rag import RAGEngine
from core.runtime.plugin_base import PluginBase, PluginManifest


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None
        self.engine = RAGEngine()
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
    
    def index(self, content: str, source: str = "memory") -> str:
        """Index a document."""
        return self.engine.index(content, source)
    
    def search(self, query: str, limit: int = 5) -> list:
        """Semantic search."""
        return self.engine.search(query, limit)
    
    def hybrid_search(self, query: str, limit: int = 5) -> list:
        """Hybrid search."""
        return self.engine.hybrid_search(query, limit)
