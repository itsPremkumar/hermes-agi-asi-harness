"""Memory visualization and debugging dashboard for ContextVault."""

from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryDashboard:
    """Generate visual representations of memory store state."""

    def __init__(self, store: Any) -> None:
        self.store = store

    def tier_distribution(self) -> Dict[str, int]:
        """Get memory count per tier for visualization."""
        return self.store.get_tier_stats()

    def type_distribution(self) -> Dict[str, int]:
        """Get memory count per type."""
        type_counts: Dict[str, int] = Counter()
        for mem in self.store.list_memories(include_archived=True):
            type_counts[mem.memory_type.value] += 1
        return dict(type_counts)

    def importance_distribution(self, bins: int = 5) -> Dict[str, int]:
        """Get memory distribution by importance buckets."""
        distribution: Dict[str, int] = {f"{i/bins:.1f}-{(i+1)/bins:.1f}": 0 for i in range(bins)}
        for mem in self.store.list_memories():
            importance = mem.metadata.importance
            bucket = min(int(importance * bins), bins - 1)
            key = f"{bucket/bins:.1f}-{(bucket+1)/bins:.1f}"
            distribution[key] += 1
        return distribution

    def access_heatmap(self, top_k: int = 20) -> List[Dict[str, Any]]:
        """Generate access frequency data for heatmap visualization."""
        memories = self.store.list_memories()
        sorted_mems = sorted(memories, key=lambda m: m.access_count, reverse=True)
        return [
            {
                "id": m.id[:8],
                "content": m.content[:50],
                "access_count": m.access_count,
                "tier": m.tier.value,
                "last_accessed": m.accessed_at,
            }
            for m in sorted_mems[:top_k]
        ]

    def forgetting_curve_data(self) -> List[Dict[str, Any]]:
        """Generate data points for forgetting curve visualization."""
        from contextvault.relevance import RelevanceScorer

        scorer = RelevanceScorer()
        data_points = []

        for mem in self.store.list_memories():
            curve = scorer.forgetting_curve_score(mem)
            data_points.append({
                "id": mem.id[:8],
                "retention": curve,
                "access_count": mem.access_count,
                "age_hours": (time.time() - mem.accessed_at) / 3600,
            })

        return sorted(data_points, key=lambda x: x["age_hours"])

    def relation_graph(self) -> Dict[str, Any]:
        """Generate graph data for memory relations."""
        nodes = []
        edges = []

        for mem in self.store.list_memories():
            nodes.append({
                "id": mem.id,
                "label": mem.content[:30],
                "tier": mem.tier.value,
                "type": mem.memory_type.value,
                "importance": mem.metadata.importance,
            })

        for mem in self.store.list_memories():
            relations = self.store.get_relations(mem.id)
            for rel in relations:
                if rel.source_id == mem.id:  # Avoid duplicates
                    edges.append({
                        "source": rel.source_id,
                        "target": rel.target_id,
                        "type": rel.relation_type,
                        "strength": rel.strength,
                    })

        return {"nodes": nodes, "edges": edges}

    def tag_cloud_data(self) -> Dict[str, int]:
        """Generate tag frequency data for word cloud visualization."""
        tag_counts: Dict[str, int] = Counter()
        for mem in self.store.list_memories():
            for tag in mem.metadata.tags:
                tag_counts[tag] += 1
        return dict(tag_counts.most_common(50))

    def activity_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Generate activity timeline data."""
        now = time.time()
        cutoff = now - (hours * 3600)
        buckets: Dict[int, Dict[str, int]] = {}

        for mem in self.store.list_memories(include_archived=True):
            if mem.created_at >= cutoff:
                hour_bucket = int((now - mem.created_at) / 3600)
                bucket = buckets.setdefault(hour_hour := hour_bucket, {"created": 0, "accessed": 0})
                bucket["created"] += 1
                if mem.accessed_at >= cutoff:
                    bucket["accessed"] += 1

        return [
            {"hour": h, **data}
            for h, data in sorted(buckets.items())
        ]

    def full_report(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard report."""
        return {
            "stats": self.store.get_stats(),
            "tier_distribution": self.tier_distribution(),
            "type_distribution": self.type_distribution(),
            "importance_distribution": self.importance_distribution(),
            "top_accessed": self.access_heatmap(10),
            "forgetting_curve": self.forgetting_curve_data(),
            "tag_cloud": self.tag_cloud_data(),
            "relation_graph": self.relation_graph(),
            "generated_at": time.time(),
        }


def format_dashboard_text(report: Dict[str, Any]) -> str:
    """Format a dashboard report as readable text."""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("       ContextVault Memory Dashboard")
    lines.append("=" * 60)

    # Stats
    stats = report.get("stats", {})
    lines.append("")
    lines.append("--- Store Statistics ---")
    lines.append(f"  Total Stored:     {stats.get('total_stored', 0)}")
    lines.append(f"  Total Archived:   {stats.get('total_archived', 0)}")
    lines.append(f"  Total Consolidated: {stats.get('total_consolidated', 0)}")
    lines.append(f"  Relations:        {stats.get('relations', 0)}")

    # Tier distribution
    tiers = report.get("tier_distribution", {})
    if tiers:
        lines.append("")
        lines.append("--- Tier Distribution ---")
        max_count = max(tiers.values()) if tiers else 1
        for tier, count in tiers.items():
            bar = "#" * int(40 * count / max(max_count, 1))
            lines.append(f"  {tier:12s} [{bar}] {count}")

    # Type distribution
    types = report.get("type_distribution", {})
    if types:
        lines.append("")
        lines.append("--- Type Distribution ---")
        for mtype, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {mtype:12s}: {count}")

    # Top accessed
    top = report.get("top_accessed", [])
    if top:
        lines.append("")
        lines.append("--- Top Accessed Memories ---")
        for item in top[:5]:
            lines.append(f"  [{item['access_count']:4d}] {item['content'][:40]}")

    # Tags
    tags = report.get("tag_cloud", {})
    if tags:
        lines.append("")
        lines.append("--- Top Tags ---")
        for tag, count in list(tags.items())[:10]:
            lines.append(f"  {tag}: {count}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
