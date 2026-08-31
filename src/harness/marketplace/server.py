"""Marketplace server — plugin discovery, browsing, search."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PluginListing:
    """A plugin listing in the marketplace."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    downloads: int = 0
    rating: float = 0.0
    tags: list[str] = field(default_factory=list)
    category: str = ""
    dependencies: list[str] = field(default_factory=list)
    icon_url: str = ""
    homepage: str = ""
    license: str = "MIT"
    size_bytes: int = 0
    created_at: str = ""
    updated_at: str = ""
    compatibility: str = ">=1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchQuery:
    """Query parameters for searching the marketplace."""

    keyword: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    author: str = ""
    min_rating: float = 0.0
    sort_by: str = "relevance"  # relevance, downloads, rating, newest
    limit: int = 50
    offset: int = 0


@dataclass
class SearchResult:
    """Result of a marketplace search."""

    listings: list[PluginListing] = field(default_factory=list)
    total: int = 0
    query: Optional[SearchQuery] = None
    page: int = 0
    has_more: bool = False


class MarketplaceServer:
    """Plugin marketplace server — discover, browse, search plugins."""

    def __init__(self):
        self._lock = threading.RLock()
        self._listings: dict[str, PluginListing] = {}
        self._categories: dict[str, list[str]] = {}  # category -> [ids]

    def publish(self, listing: PluginListing) -> bool:
        """Publish a plugin listing. Returns False if ID already exists with higher version."""
        with self._lock:
            existing = self._listings.get(listing.id)
            if existing and existing.version >= listing.version:
                return False
            self._listings[listing.id] = listing
            if listing.category:
                self._categories.setdefault(listing.category, []).append(listing.id)
            return True

    def unpublish(self, plugin_id: str) -> bool:
        """Remove a plugin listing from the marketplace."""
        with self._lock:
            listing = self._listings.pop(plugin_id, None)
            if listing is None:
                return False
            if listing.category:
                cat_list = self._categories.get(listing.category, [])
                if plugin_id in cat_list:
                    cat_list.remove(plugin_id)
            return True

    def get_listing(self, plugin_id: str) -> Optional[PluginListing]:
        """Get a plugin listing by ID."""
        with self._lock:
            return self._listings.get(plugin_id)

    def get_all_listings(self) -> list[PluginListing]:
        """Get all plugin listings."""
        with self._lock:
            return list(self._listings.values())

    def get_categories(self) -> list[str]:
        """Get all available categories."""
        with self._lock:
            return list(self._categories.keys())

    def get_by_category(self, category: str) -> list[PluginListing]:
        """Get all listings in a category."""
        with self._lock:
            ids = self._categories.get(category, [])
            return [self._listings[i] for i in ids if i in self._listings]

    def get_by_author(self, author: str) -> list[PluginListing]:
        """Get all listings by a specific author."""
        with self._lock:
            return [l for l in self._listings.values() if l.author == author]

    def get_by_tag(self, tag: str) -> list[PluginListing]:
        """Get all listings with a specific tag."""
        with self._lock:
            return [l for l in self._listings.values() if tag in l.tags]

    def get_top_rated(self, limit: int = 10) -> list[PluginListing]:
        """Get top-rated plugins."""
        with self._lock:
            sorted_listings = sorted(self._listings.values(), key=lambda l: l.rating, reverse=True)
            return sorted_listings[:limit]

    def get_most_downloaded(self, limit: int = 10) -> list[PluginListing]:
        """Get most downloaded plugins."""
        with self._lock:
            sorted_listings = sorted(self._listings.values(), key=lambda l: l.downloads, reverse=True)
            return sorted_listings[:limit]

    def search(self, query: SearchQuery) -> SearchResult:
        """Search the marketplace with filters and sorting."""
        with self._lock:
            results = list(self._listings.values())

            # Keyword filter
            if query.keyword:
                keyword_lower = query.keyword.lower()
                results = [
                    l for l in results
                    if keyword_lower in l.name.lower()
                    or keyword_lower in l.description.lower()
                    or keyword_lower in l.id.lower()
                    or any(keyword_lower in tag.lower() for tag in l.tags)
                ]

            # Category filter
            if query.category:
                results = [l for l in results if l.category == query.category]

            # Tags filter
            if query.tags:
                results = [l for l in results if any(tag in l.tags for tag in query.tags)]

            # Author filter
            if query.author:
                results = [l for l in results if l.author == query.author]

            # Rating filter
            if query.min_rating > 0:
                results = [l for l in results if l.rating >= query.min_rating]

            # Sort
            if query.sort_by == "downloads":
                results.sort(key=lambda l: l.downloads, reverse=True)
            elif query.sort_by == "rating":
                results.sort(key=lambda l: l.rating, reverse=True)
            elif query.sort_by == "newest":
                results.sort(key=lambda l: l.updated_at, reverse=True)
            # relevance is default order after filtering

            total = len(results)

            # Pagination
            start = query.offset
            end = start + query.limit
            paginated = results[start:end]

            return SearchResult(
                listings=paginated,
                total=total,
                query=query,
                page=query.offset // query.limit if query.limit > 0 else 0,
                has_more=end < total,
            )

    def count(self) -> int:
        """Get the total number of listings."""
        with self._lock:
            return len(self._listings)

    def increment_downloads(self, plugin_id: str) -> bool:
        """Increment download count for a plugin."""
        with self._lock:
            listing = self._listings.get(plugin_id)
            if listing is None:
                return False
            listing.downloads += 1
            return True

    def update_rating(self, plugin_id: str, new_rating: float) -> bool:
        """Update the rating for a plugin."""
        with self._lock:
            listing = self._listings.get(plugin_id)
            if listing is None:
                return False
            listing.rating = max(0.0, min(5.0, new_rating))
            return True

    def clear(self) -> None:
        """Clear all listings."""
        with self._lock:
            self._listings.clear()
            self._categories.clear()
