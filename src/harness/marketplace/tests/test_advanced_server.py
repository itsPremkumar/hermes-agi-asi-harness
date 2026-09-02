"""Tests for Advanced Plugin Marketplace."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from harness.marketplace.advanced_server import (
    PluginMarketplace,
    SecurityScanner,
    Package,
    PackageStatus,
    SearchResult,
)


class TestPackage:
    def test_create(self):
        pkg = Package(
            id="test-pkg",
            name="Test Package",
            version="1.0.0",
            description="A test package",
            author="test",
            source_url="https://example.com",
            checksum="abc123",
        )
        assert pkg.id == "test-pkg"
        assert pkg.status == PackageStatus.PENDING

    def test_with_dependencies(self):
        pkg = Package(
            id="test-pkg",
            name="Test",
            version="1.0.0",
            description="Test",
            author="test",
            source_url="https://example.com",
            checksum="abc",
            dependencies=["dep1", "dep2"],
        )
        assert len(pkg.dependencies) == 2


class TestPluginMarketplace:
    def test_create(self):
        mp = PluginMarketplace()
        assert mp is not None

    def test_publish(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "Test", "1.0", "Desc", "author", "url", "checksum")
        assert mp.publish(pkg) is True

    def test_publish_duplicate(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "Test", "1.0", "Desc", "author", "url", "checksum")
        mp.publish(pkg)
        assert mp.publish(pkg) is False

    def test_get(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "Test", "1.0", "Desc", "author", "url", "checksum")
        mp.publish(pkg)
        result = mp.get("p1")
        assert result is not None
        assert result.id == "p1"

    def test_get_not_found(self):
        mp = PluginMarketplace()
        assert mp.get("nonexistent") is None

    def test_update(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "Test", "1.0", "Desc", "author", "url", "checksum")
        mp.publish(pkg)
        assert mp.update("p1", name="New Name") is True

    def test_deprecate(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "Test", "1.0", "Desc", "author", "url", "checksum")
        mp.publish(pkg)
        assert mp.deprecate("p1") is True
        assert mp.get("p1").status == PackageStatus.DEPRECATED

    def test_search_empty(self):
        mp = PluginMarketplace()
        result = mp.search("")
        assert isinstance(result, SearchResult)
        assert result.total == 0

    def test_search_by_name(self):
        mp = PluginMarketplace()
        mp.publish(Package("p1", "Weather Plugin", "1.0", "Weather", "a", "url", "c"))
        mp.publish(Package("p2", "Chat Plugin", "1.0", "Chat", "a", "url", "c"))
        result = mp.search("weather")
        assert result.total == 1

    def test_search_by_tags(self):
        mp = PluginMarketplace()
        mp.publish(Package("p1", "P1", "1.0", "D", "a", "url", "c", tags=["web", "api"]))
        mp.publish(Package("p2", "P2", "1.0", "D", "a", "url", "c", tags=["cli"]))
        result = mp.search(tags=["web"])
        assert result.total == 1

    def test_search_by_author(self):
        mp = PluginMarketplace()
        mp.publish(Package("p1", "P1", "1.0", "D", "alice", "url", "c"))
        mp.publish(Package("p2", "P2", "1.0", "D", "bob", "url", "c"))
        result = mp.search(author="alice")
        assert result.total == 1

    def test_search_by_status(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "P1", "1.0", "D", "a", "url", "c")
        mp.publish(pkg)
        result = mp.search(status=PackageStatus.PENDING)
        assert result.total == 1

    def test_install_not_found(self):
        mp = PluginMarketplace()
        result = mp.install("nonexistent", "/tmp")
        assert result["status"] == "error"

    def test_install_deprecated(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "P1", "1.0", "D", "a", "url", "c")
        mp.publish(pkg)
        mp.deprecate("p1")
        result = mp.install("p1", "/tmp")
        assert result["status"] == "error"

    def test_rate(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "P1", "1.0", "D", "a", "url", "c")
        mp.publish(pkg)
        result = mp.rate("p1", 5.0, "Great!", "user1")
        assert result["status"] == "success"
        assert mp.get("p1").rating == 5.0

    def test_rate_invalid(self):
        mp = PluginMarketplace()
        pkg = Package("p1", "P1", "1.0", "D", "a", "url", "c")
        mp.publish(pkg)
        result = mp.rate("p1", 6.0)
        assert result["status"] == "error"

    def test_get_stats(self):
        mp = PluginMarketplace()
        mp.publish(Package("p1", "P1", "1.0", "D", "a", "url", "c"))
        stats = mp.get_stats()
        assert stats["total_packages"] == 1
        assert stats["total_downloads"] == 0


class TestSecurityScanner:
    def test_create(self):
        scanner = SecurityScanner()
        assert scanner is not None

    def test_scan_no_checksum(self):
        scanner = SecurityScanner()
        pkg = Package("p1", "P1", "1.0", "D", "a", "url", "")
        result = scanner.scan(pkg)
        assert result["status"] == "failed"

    def test_scan_passed(self):
        scanner = SecurityScanner()
        pkg = Package("p1", "P1", "1.0", "D", "a", "url", "abc123")
        result = scanner.scan(pkg)
        assert result["status"] == "passed"

    def test_blacklist_url(self):
        scanner = SecurityScanner()
        scanner.blacklist_url("malicious.com")
        pkg = Package("p1", "P1", "1.0", "D", "a", "https://malicious.com/pkg", "abc")
        result = scanner.scan(pkg)
        assert result["status"] == "failed"
