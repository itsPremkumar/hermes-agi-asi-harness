"""Tests for AgentOS plugin system."""

from __future__ import annotations

import pytest

from agentos.plugins import (
    Plugin,
    PluginError,
    PluginManager,
    PluginManifest,
)


class TestPluginManifest:
    def test_create_manifest(self) -> None:
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
        )
        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"

    def test_to_dict(self) -> None:
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            permissions=["read"],
        )
        d = manifest.to_dict()
        assert d["name"] == "test"
        assert d["permissions"] == ["read"]

    def test_from_dict(self) -> None:
        data = {"name": "test", "version": "1.0.0", "description": "desc"}
        manifest = PluginManifest.from_dict(data)
        assert manifest.name == "test"


class TestPluginManager:
    def test_create_manager(self) -> None:
        manager = PluginManager()
        assert manager is not None

    def test_load_from_manifest(self) -> None:
        manager = PluginManager()
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            description="Test plugin",
        )
        plugin = manager.load_from_manifest(manifest)
        assert plugin.manifest.name == "test"
        assert plugin.loaded is True

    def test_get_plugin(self) -> None:
        manager = PluginManager()
        manifest = PluginManifest(name="test", version="1.0.0")
        manager.load_from_manifest(manifest)
        plugin = manager.get("test")
        assert plugin is not None
        assert plugin.manifest.name == "test"

    def test_list_plugins(self) -> None:
        manager = PluginManager()
        manager.load_from_manifest(PluginManifest(name="p1", version="1.0.0"))
        manager.load_from_manifest(PluginManifest(name="p2", version="1.0.0"))
        assert len(manager.list_plugins()) == 2

    def test_unload_plugin(self) -> None:
        manager = PluginManager()
        manager.load_from_manifest(PluginManifest(name="test", version="1.0.0"))
        assert manager.unload("test") is True
        assert manager.get("test") is None

    def test_load_python_plugin(self, tmp_path) -> None:
        # Create plugin code
        plugin_code = """
def main(input_data):
    return {"result": input_data.upper()}
"""
        plugin_file = tmp_path / "plugin.py"
        plugin_file.write_text(plugin_code)

        # Create manifest
        manifest_data = {
            "name": "upper",
            "version": "1.0.0",
            "entry_point": "main",
        }
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(
            __import__("json").dumps(manifest_data)
        )

        manager = PluginManager()
        plugin = manager.load_from_file(manifest_file)
        assert plugin.loaded is True

    def test_execute_python_plugin(self, tmp_path) -> None:
        # Create plugin code - must be named same as manifest but with .py extension
        plugin_code = """
def main(input_data):
    return input_data * 2
"""
        # The plugin manager looks for a .py file with the same stem as the manifest
        plugin_file = tmp_path / "manifest.py"
        plugin_file.write_text(plugin_code)

        manifest_data = {
            "name": "doubler",
            "version": "1.0.0",
            "entry_point": "main",
        }
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(
            __import__("json").dumps(manifest_data)
        )

        manager = PluginManager()
        manager.load_from_file(manifest_file)
        result = manager.execute("doubler", 5)
        assert result == 10

    def test_execute_nonexistent_plugin(self) -> None:
        manager = PluginManager()
        with pytest.raises(PluginError, match="Plugin not found"):
            manager.execute("nonexistent", None)

    def test_validate_plugin(self) -> None:
        manager = PluginManager()
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            permissions=["read", "write"],
        )
        manager.load_from_manifest(manifest)
        issues = manager.validate("test")
        assert len(issues) == 0

    def test_validate_dangerous_permissions(self) -> None:
        manager = PluginManager()
        manifest = PluginManifest(
            name="dangerous",
            version="1.0.0",
            permissions=["filesystem.write", "network.raw"],
        )
        manager.load_from_manifest(manifest)
        issues = manager.validate("dangerous")
        assert len(issues) == 2

    def test_register_hook(self) -> None:
        manager = PluginManager()
        events: list[str] = []
        manager.register_hook("loaded", lambda p: events.append(p.manifest.name))
        manager.load_from_manifest(PluginManifest(name="test", version="1.0.0"))
        assert events == ["test"]
