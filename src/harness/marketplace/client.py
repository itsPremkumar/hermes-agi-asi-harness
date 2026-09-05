"""Marketplace client stub."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketplaceConfig:
    url: str = "https://plugins.hermes.ai"
    token: str = ""

class MarketplaceClient:
    def __init__(self, config: MarketplaceConfig = None):
        self.config = config or MarketplaceConfig()
