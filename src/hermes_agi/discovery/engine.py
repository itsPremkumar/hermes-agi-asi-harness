"""Meta-Discovery Engine — finds and catalogs every available feature."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredFeature:
    """A discovered feature."""
    name: str
    category: str
    description: str
    source: str
    capabilities: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class MetaDiscovery:
    """Discovers and catalogs all available features."""
    
    def __init__(self, config: Any | None = None):
        self.config = config or {}
        self.features: dict[str, DiscoveredFeature] = {}
    
    @classmethod
    async def create(cls, config: Any | None = None) -> "MetaDiscovery":
        """Create the discovery engine."""
        discovery = cls(config)
        await discovery._discover_all()
        return discovery
    
    async def _discover_all(self) -> None:
        """Discover all features."""
        # Add core features
        self.features["kernel"] = DiscoveredFeature(
            name="kernel",
            category="core",
            description="harnix kernel lifecycle management",
            source="hermes_agi",
            capabilities=["lifecycle", "tasks", "state"],
        )
        self.features["safety"] = DiscoveredFeature(
            name="safety",
            category="core",
            description="R0-R6 safety governance",
            source="hermes_agi",
            capabilities=["risk", "invariants", "audit"],
        )
        self.features["bridge"] = DiscoveredFeature(
            name="bridge",
            category="core",
            description="Hermes Agent integration bridge",
            source="hermes_agi",
            capabilities=["mcp", "tools", "integration"],
        )
    
    def find_by_capability(self, capability: str) -> list[DiscoveredFeature]:
        """Find features by capability."""
        return [
            f for f in self.features.values()
            if capability.lower() in [c.lower() for c in f.capabilities]
        ]
    
    def search(self, query: str) -> list[DiscoveredFeature]:
        """Search features."""
        query_lower = query.lower()
        return [
            f for f in self.features.values()
            if query_lower in f.name.lower() or query_lower in f.description.lower()
        ]
    
    def get_all_features(self) -> dict[str, list[DiscoveredFeature]]:
        """Get all features organized by category."""
        categories: dict[str, list[DiscoveredFeature]] = {}
        for feature in self.features.values():
            if feature.category not in categories:
                categories[feature.category] = []
            categories[feature.category].append(feature)
        return categories
