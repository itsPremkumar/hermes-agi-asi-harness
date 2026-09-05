"""Plugin Marketplace — discover, install, and manage plugins."""

from __future__ import annotations

from harness.marketplace.client import MarketplaceClient, MarketplaceConfig
from harness.marketplace.installer import InstallResult, PluginInstaller, UninstallResult
from harness.marketplace.manager import PluginEntry, PluginManager, PluginState
from harness.marketplace.resolver import MarketplaceResolver, ResolveResult
from harness.marketplace.server import MarketplaceServer, SearchQuery, SearchResult
from harness.marketplace.validator import PluginValidator, SecurityScan, ValidationResult

__all__ = [
    "MarketplaceServer",
    "SearchQuery",
    "SearchResult",
    "PluginInstaller",
    "InstallResult",
    "UninstallResult",
    "PluginValidator",
    "ValidationResult",
    "SecurityScan",
    "MarketplaceResolver",
    "ResolveResult",
    "MarketplaceClient",
    "MarketplaceConfig",
    "PluginManager",
    "PluginEntry",
    "PluginState",
]
