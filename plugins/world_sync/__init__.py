"""
World Sync Plugin — External World State Synchronization

Connects to: GitHub, ArXiv, HuggingFace, news feeds, web sources.
Tracks: external changes, API changes, security advisories,
opportunities, competitive intelligence.
"""

import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class SyncSource(str, Enum):
    GITHUB = "github"
    ARXIV = "arxiv"
    HUGGINGFACE = "huggingface"
    NEWS = "news"
    WEB = "web"
    RSS = "rss"


@dataclass
class WorldChange:
    source: str
    title: str
    url: str
    summary: str
    relevance_score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    change_id: str = field(default_factory=lambda: f"CHG-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "change_id": self.change_id,
        }


class WorldSync:
    """Synchronize with external world state."""

    def __init__(self):
        self._changes: List[WorldChange] = []
        self._last_sync: Dict[str, float] = {}
        self._sync_intervals: Dict[str, int] = {
            SyncSource.GITHUB.value: 3600,  # 1 hour
            SyncSource.ARXIV.value: 86400,  # 1 day
            SyncSource.HUGGINGFACE.value: 86400,  # 1 day
            SyncSource.NEWS.value: 1800,  # 30 min
            SyncSource.WEB.value: 7200,  # 2 hours
            SyncSource.RSS.value: 1800,  # 30 min
        }

    def should_sync(self, source: str) -> bool:
        """Check if a source needs syncing."""
        last = self._last_sync.get(source, 0)
        interval = self._sync_intervals.get(source, 3600)
        return (time.time() - last) > interval

    def record_sync(self, source: str):
        self._last_sync[source] = time.time()

    def ingest_change(self, source: str, title: str, url: str,
                      summary: str, relevance_score: float = 0.5,
                      tags: List[str] = None) -> WorldChange:
        change = WorldChange(
            source=source,
            title=title,
            url=url,
            summary=summary,
            relevance_score=relevance_score,
            tags=tags or [],
        )
        self._changes.append(change)
        return change

    def get_relevant_changes(self, min_relevance: float = 0.5,
                             limit: int = 20) -> List[WorldChange]:
        relevant = [c for c in self._changes if c.relevance_score >= min_relevance]
        relevant.sort(key=lambda c: c.relevance_score, reverse=True)
        return relevant[:limit]

    def get_changes_by_source(self, source: str, limit: int = 20) -> List[WorldChange]:
        changes = [c for c in self._changes if c.source == source]
        changes.sort(key=lambda c: c.timestamp, reverse=True)
        return changes[:limit]

    def get_opportunities(self) -> List[WorldChange]:
        """Get high-relevance changes that represent opportunities."""
        return [c for c in self._changes
                if c.relevance_score >= 0.7 and "opportunity" in c.tags]

    def get_stats(self) -> Dict[str, Any]:
        by_source: Dict[str, int] = {}
        for c in self._changes:
            by_source[c.source] = by_source.get(c.source, 0) + 1
        return {
            "total_changes": len(self._changes),
            "by_source": by_source,
            "sources_synced": len(self._last_sync),
            "high_relevance": sum(1 for c in self._changes if c.relevance_score >= 0.7),
        }


class WorldSyncPlugin:
    def __init__(self):
        self.engine = WorldSync()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "stats": self.engine.get_stats(),
        }


async def create(kernel=None):
    plugin = WorldSyncPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
