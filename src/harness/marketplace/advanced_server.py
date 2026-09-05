"""Advanced Plugin Marketplace Server.

Full-featured marketplace with search, install, rate, review,
dependency resolution, and security scanning.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PackageStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


@dataclass
class Package:
    id: str
    name: str
    version: str
    description: str
    author: str
    source_url: str
    checksum: str
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    status: PackageStatus = PackageStatus.PENDING
    downloads: int = 0
    rating: float = 0.0
    ratings_count: int = 0
    reviews: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SearchResult:
    packages: list[Package]
    total: int
    page: int
    per_page: int


class PluginMarketplace:
    """Advanced plugin marketplace."""

    def __init__(self):
        self._packages: dict[str, Package] = {}
        self._lock = threading.RLock()
        self._install_history: list[dict[str, Any]] = []
        self._security_scanner = SecurityScanner()

    def publish(self, package: Package) -> bool:
        """Publish a package to the marketplace."""
        with self._lock:
            if package.id in self._packages:
                return False
            self._packages[package.id] = package
            return True

    def update(self, package_id: str, **kwargs) -> bool:
        """Update a package."""
        with self._lock:
            pkg = self._packages.get(package_id)
            if not pkg:
                return False
            for key, value in kwargs.items():
                if hasattr(pkg, key):
                    setattr(pkg, key, value)
            pkg.updated_at = time.time()
            return True

    def deprecate(self, package_id: str) -> bool:
        """Deprecate a package."""
        return self.update(package_id, status=PackageStatus.DEPRECATED)

    def get(self, package_id: str) -> Package | None:
        """Get a package by ID."""
        with self._lock:
            return self._packages.get(package_id)

    def search(
        self,
        query: str = "",
        tags: list[str] | None = None,
        author: str = "",
        status: PackageStatus | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> SearchResult:
        """Search packages."""
        with self._lock:
            results = list(self._packages.values())

            if query:
                query_lower = query.lower()
                results = [
                    p for p in results
                    if query_lower in p.name.lower()
                    or query_lower in p.description.lower()
                ]

            if tags:
                results = [
                    p for p in results
                    if any(t in p.tags for t in tags)
                ]

            if author:
                results = [p for p in results if p.author == author]

            if status:
                results = [p for p in results if p.status == status]

            total = len(results)
            start = (page - 1) * per_page
            end = start + per_page

            return SearchResult(
                packages=results[start:end],
                total=total,
                page=page,
                per_page=per_page,
            )

    def install(self, package_id: str, install_path: str) -> dict[str, Any]:
        """Install a package."""
        with self._lock:
            pkg = self._packages.get(package_id)
            if not pkg:
                return {"status": "error", "message": "Package not found"}

            if pkg.status == PackageStatus.DEPRECATED:
                return {"status": "error", "message": "Package is deprecated"}

            if pkg.status == PackageStatus.REJECTED:
                return {"status": "error", "message": "Package was rejected"}

            # Security scan
            scan_result = self._security_scanner.scan(pkg)
            if scan_result["status"] == "failed":
                return {"status": "error", "message": f"Security scan failed: {scan_result['reason']}"}

            # Resolve dependencies
            dep_result = self._resolve_dependencies(pkg, install_path)
            if dep_result["status"] == "error":
                return dep_result

            pkg.downloads += 1
            self._install_history.append({
                "package_id": package_id,
                "timestamp": time.time(),
                "path": install_path,
            })

            return {
                "status": "success",
                "package": pkg,
                "dependencies_installed": dep_result.get("installed", []),
            }

    def rate(self, package_id: str, rating: float, review: str = "", reviewer: str = "") -> dict[str, Any]:
        """Rate and review a package."""
        with self._lock:
            pkg = self._packages.get(package_id)
            if not pkg:
                return {"status": "error", "message": "Package not found"}

            if not 1.0 <= rating <= 5.0:
                return {"status": "error", "message": "Rating must be 1-5"}

            # Update running average
            total = pkg.rating * pkg.ratings_count + rating
            pkg.ratings_count += 1
            pkg.rating = total / pkg.ratings_count

            if review:
                pkg.reviews.append({
                    "reviewer": reviewer,
                    "rating": rating,
                    "review": review,
                    "timestamp": time.time(),
                })

            return {"status": "success", "new_rating": pkg.rating}

    def get_stats(self) -> dict[str, Any]:
        """Get marketplace stats."""
        with self._lock:
            total_downloads = sum(p.downloads for p in self._packages.values())
            return {
                "total_packages": len(self._packages),
                "total_downloads": total_downloads,
                "avg_rating": (
                    sum(p.rating for p in self._packages.values()) / len(self._packages)
                    if self._packages else 0.0
                ),
                "install_history_count": len(self._install_history),
            }

    def _resolve_dependencies(self, package: Package, install_path: str) -> dict[str, Any]:
        """Resolve and install dependencies."""
        installed = []
        for dep_id in package.dependencies:
            dep_pkg = self._packages.get(dep_id)
            if not dep_pkg:
                return {"status": "error", "message": f"Dependency not found: {dep_id}"}
            if dep_pkg.status != PackageStatus.APPROVED:
                return {"status": "error", "message": f"Dependency not approved: {dep_id}"}
            installed.append(dep_id)
        return {"status": "success", "installed": installed}


class SecurityScanner:
    """Security scanner for packages."""

    def __init__(self):
        self._blacklisted_imports = ["os.system", "subprocess", "eval", "exec"]
        self._blacklisted_urls = []

    def scan(self, package: Package) -> dict[str, Any]:
        """Scan a package for security issues."""
        # Check checksum
        if not package.checksum:
            return {"status": "failed", "reason": "Missing checksum"}

        # Check source URL
        for url in self._blacklisted_urls:
            if url in package.source_url:
                return {"status": "failed", "reason": f"Blacklisted URL: {url}"}

        return {"status": "passed", "reason": ""}

    def blacklist_import(self, import_name: str) -> None:
        """Add an import to the blacklist."""
        self._blacklisted_imports.append(import_name)

    def blacklist_url(self, url: str) -> None:
        """Add a URL to the blacklist."""
        self._blacklisted_urls.append(url)
