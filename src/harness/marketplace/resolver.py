"""Marketplace resolver stub."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ResolveResult:
    resolved: bool
    dependencies: list[str] = None

class MarketplaceResolver:
    def resolve(self, package_id: str) -> ResolveResult:
        return ResolveResult(resolved=True)
