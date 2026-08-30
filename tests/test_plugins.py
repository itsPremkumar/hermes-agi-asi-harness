"""
Tests for the plugin system.

Covers:
- Plugin base classes and manifests
- Hook registry
- Plugin registry
- Plugin loader
- Plugin manager
- Example plugins
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from harness.plugins.base import (
    Plugin,
    PluginManifest,
    PluginContext,
    PluginType,
    ToolPlugin,
    GuardPlugin,
    Capability,
    ExecutionResult,
)
from harness.plugins.hooks import (
    HookRegistry,
    HookEvent,
    Priority,
    HOOK_EVENTS,
)
from harness.plugins.registry import Registry
from harness.plugins.loader import PluginLoader, PluginLoadError
from harness.plugins.manager import PluginManager, PluginManagerError
from harness.plugins.examples import (
    HelloWorldPlugin,
    SafetyGuardPlugin,
    MetricsPlugin,
)


# ===========================================================================
# Plugin Manifest Tests
# ===========================================================================


class TestPluginManifest:
    def test_create_manifest(self):
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.TOOL,
            description="A test plugin",
        )
        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.plugin_type == PluginType.TOOL
        assert manifest.id == "test-plugin@1.0.0"

    def test_manifest_serialization(self):
        manifest = PluginManifest(
            name="test",
            version="2.0.0",
            plugin_type=PluginType.GUARD,
            description="Test",
            permissions=["network:outbound"],
            dependencies=["base-plugin"],
        )
        data = manifest.to_dict()
        restored = PluginManifest.from_dict(data)
        assert restored.name == manifest.name
        assert restored.version == manifest.version
        assert restored.plugin_type == manifest.plugin_type
        assert restored.permissions == manifest.permissions
        assert restored.dependencies == manifest.dependencies

    def test_manifest_from_dict_minimal(self):
        data = {"name": "minimal", "version": "0.1.0", "type": "tool"}
        manifest = PluginManifest.from_dict(data)
        assert manifest.name == "minimal"
        assert manifest.plugin_type == PluginType.TOOL
        assert manifest.permissions == []

    def test_manifest_equality(self):
        m1 = PluginManifest(name="a", version="1.0.0", plugin_type=PluginType.TOOL)
        m2 = PluginManifest(name="a", version="1.0.0", plugin_type=PluginType.TOOL)
        assert m1.id == m2.id


# ===========================================================================
# Hook Registry Tests
# ===========================================================================


class TestHookRegistry:
    @pytest.mark.asyncio
    async def test_register_and_fire(self):
        registry = HookRegistry()
        results = []

        async def handler(event):
            results.append(event.name)

        registry.register("on_before_execute", handler)
        await registry.fire("on_before_execute")
        assert results == ["on_before_execute"]

    @pytest.mark.asyncio
    async def test_fire_with_data(self):
        registry = HookRegistry()
        received = []

        async def handler(event):
            received.append(event.data.get("value"))

        registry.register("on_after_execute", handler)
        await registry.fire("on_after_execute", value=42)
        assert received == [42]

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        registry = HookRegistry()
        order = []

        async def handler_low(event):
            order.append("low")

        async def handler_high(event):
            order.append("high")

        async def handler_normal(event):
            order.append("normal")

        registry.register("on_error", handler_low, priority=Priority.LOW)
        registry.register("on_error", handler_high, priority=Priority.HIGH)
        registry.register("on_error", handler_normal, priority=Priority.NORMAL)

        await registry.fire("on_error")
        assert order == ["high", "normal", "low"]

    def test_unregister(self):
        registry = HookRegistry()
        results = []

        async def handler(event):
            results.append("called")

        hook_id = registry.register("on_before_execute", handler)
        assert registry.unregister(hook_id) is True
        # Verify hook count decreased
        assert registry.hook_count == 0

    def test_unregister_all_for_plugin(self):
        registry = HookRegistry()

        async def handler(event):
            pass

        registry.register("on_before_execute", handler, plugin_id="p1")
        registry.register("on_after_execute", handler, plugin_id="p1")
        registry.register("on_error", handler, plugin_id="p2")

        count = registry.unregister_all("p1")
        assert count == 2
        assert registry.hook_count == 1

    def test_unknown_event_raises(self):
        registry = HookRegistry()

        async def handler(event):
            pass

        with pytest.raises(ValueError, match="Unknown hook event"):
            registry.register("unknown_event", handler)

    @pytest.mark.asyncio
    async def test_event_cancellation(self):
        registry = HookRegistry()
        results = []

        async def cancel_handler(event):
            event.cancel()
            results.append("first")

        async def skipped_handler(event):
            results.append("second")

        registry.register("on_before_execute", cancel_handler, priority=Priority.HIGHEST)
        registry.register("on_before_execute", skipped_handler, priority=Priority.LOW)

        event = await registry.fire("on_before_execute")
        assert event.cancelled is True
        assert results == ["first"]

    @pytest.mark.asyncio
    async def test_once_hook(self):
        registry = HookRegistry()
        results = []

        async def handler(event):
            results.append("called")

        registry.register("on_node_start", handler, once=True)

        await registry.fire("on_node_start")
        await registry.fire("on_node_start")

        assert results == ["called"]

    @pytest.mark.asyncio
    async def test_hook_exception_doesnt_break_chain(self):
        registry = HookRegistry()
        results = []

        async def bad_handler(event):
            raise RuntimeError("boom")

        async def good_handler(event):
            results.append("ok")

        registry.register("on_node_end", bad_handler, priority=Priority.HIGH)
        registry.register("on_node_end", good_handler, priority=Priority.LOW)

        await registry.fire("on_node_end")
        assert results == ["ok"]

    def test_get_registered_events(self):
        registry = HookRegistry()

        async def handler(event):
            pass

        registry.register("on_before_execute", handler)
        registry.register("on_after_execute", handler)

        events = registry.get_registered_events()
        assert "on_before_execute" in events
        assert "on_after_execute" in events

    @pytest.mark.asyncio
    async def test_history(self):
        registry = HookRegistry()

        async def handler(event):
            pass

        registry.register("on_before_execute", handler)
        await registry.fire("on_before_execute")
        await registry.fire("on_before_execute")

        history = registry.get_history()
        assert len(history) == 2


# ===========================================================================
# Plugin Registry Tests
# ===========================================================================


class TestRegistry:
    def test_register_and_get(self):
        registry = Registry()
        plugin = HelloWorldPlugin()
        registry.register(plugin)

        assert registry.has("hello-world")
        assert registry.get_plugin("hello-world") is plugin

    def test_register_duplicate_raises(self):
        registry = Registry()
        plugin = HelloWorldPlugin()
        registry.register(plugin)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(HelloWorldPlugin())

    def test_unregister(self):
        registry = Registry()
        plugin = HelloWorldPlugin()
        registry.register(plugin)

        entry = registry.unregister("hello-world")
        assert entry is not None
        assert registry.has("hello-world") is False

    def test_get_by_type(self):
        registry = Registry()
        registry.register(HelloWorldPlugin())
        registry.register(SafetyGuardPlugin())

        tools = registry.get_by_type(PluginType.TOOL)
        guards = registry.get_by_type(PluginType.GUARD)
        assert len(tools) == 1
        assert len(guards) == 1

    def test_activate_deactivate(self):
        registry = Registry()
        plugin = HelloWorldPlugin()
        registry.register(plugin)

        assert registry.get_active("hello-world") is not None
        registry.deactivate("hello-world")
        assert registry.get_active("hello-world") is None
        registry.activate("hello-world")
        assert registry.get_active("hello-world") is not None

    def test_list_plugins(self):
        registry = Registry()
        registry.register(HelloWorldPlugin())
        registry.register(SafetyGuardPlugin())

        plugins = registry.list_plugins()
        assert len(plugins) == 2
        names = {p.manifest.name for p in plugins}
        assert names == {"hello-world", "safety-guard"}

    def test_check_dependencies(self):
        registry = Registry()
        manifest = PluginManifest(
            name="dependent",
            version="1.0.0",
            plugin_type=PluginType.TOOL,
            dependencies=["missing-dep"],
        )
        missing = registry.check_dependencies(manifest)
        assert missing == ["missing-dep"]


# ===========================================================================
# Plugin Loader Tests
# ===========================================================================


class TestPluginLoader:
    def test_load_from_file(self):
        loader = PluginLoader()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(textwrap.dedent("""\
                from harness.plugins.base import ToolPlugin, PluginManifest, PluginType, PluginContext, Capability, ExecutionResult

                class TestPlugin(ToolPlugin):
                    def get_manifest(self):
                        return PluginManifest(name="file-test", version="1.0.0", plugin_type=PluginType.TOOL)
                    async def initialize(self, context):
                        pass
                    async def shutdown(self):
                        pass
                    def get_capabilities(self):
                        return []
                    async def execute(self, capability, params, context):
                        return ExecutionResult(success=True)

                def create_plugin():
                    return TestPlugin()
            """))
            f.flush()
            plugin = loader.load_from_file(f.name)

        assert plugin is not None
        assert plugin.get_manifest().name == "file-test"
        os.unlink(f.name)

    def test_load_from_file_not_a_plugin(self):
        loader = PluginLoader()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("x = 42\n")
            f.flush()
            plugin = loader.load_from_file(f.name)

        assert plugin is None
        os.unlink(f.name)

    def test_load_from_directory(self):
        loader = PluginLoader()
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "my_plugin.py"
            plugin_file.write_text(textwrap.dedent("""\
                from harness.plugins.base import ToolPlugin, PluginManifest, PluginType, PluginContext, Capability, ExecutionResult

                class DirTestPlugin(ToolPlugin):
                    def get_manifest(self):
                        return PluginManifest(name="dir-test", version="1.0.0", plugin_type=PluginType.TOOL)
                    async def initialize(self, context):
                        pass
                    async def shutdown(self):
                        pass
                    def get_capabilities(self):
                        return []
                    async def execute(self, capability, params, context):
                        return ExecutionResult(success=True)

                def create_plugin():
                    return DirTestPlugin()
            """), encoding="utf-8")

            plugins = loader.load_from_directory(tmpdir)
            assert len(plugins) == 1
            assert plugins[0].get_manifest().name == "dir-test"

    def test_load_from_config(self):
        loader = PluginLoader()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(textwrap.dedent("""\
                from harness.plugins.base import ToolPlugin, PluginManifest, PluginType, PluginContext, Capability, ExecutionResult

                class ConfigTestPlugin(ToolPlugin):
                    def get_manifest(self):
                        return PluginManifest(name="config-test", version="1.0.0", plugin_type=PluginType.TOOL)
                    async def initialize(self, context):
                        pass
                    async def shutdown(self):
                        pass
                    def get_capabilities(self):
                        return []
                    async def execute(self, capability, params, context):
                        return ExecutionResult(success=True)

                def create_plugin():
                    return ConfigTestPlugin()
            """))
            f.flush()

            config = {
                "plugins": [
                    {"file": f.name},
                ]
            }
            plugins = loader.load_from_config(config)

        assert len(plugins) == 1
        assert plugins[0].get_manifest().name == "config-test"
        os.unlink(f.name)


# ===========================================================================
# Plugin Manager Tests
# ===========================================================================


class TestPluginManager:
    @pytest.mark.asyncio
    async def test_load_and_initialize(self):
        manager = PluginManager()
        plugin = HelloWorldPlugin()
        name = await manager.load_plugin(plugin)
        assert name == "hello-world"
        assert manager.get_state("hello-world").state == "active"

    @pytest.mark.asyncio
    async def test_load_duplicate_raises(self):
        manager = PluginManager()
        await manager.load_plugin(HelloWorldPlugin())
        with pytest.raises(PluginManagerError, match="already loaded"):
            await manager.load_plugin(HelloWorldPlugin())

    @pytest.mark.asyncio
    async def test_unload_plugin(self):
        manager = PluginManager()
        await manager.load_plugin(HelloWorldPlugin())
        result = await manager.unload_plugin("hello-world")
        assert result is True
        assert manager.get_state("hello-world") is None

    @pytest.mark.asyncio
    async def test_get_active_plugins(self):
        manager = PluginManager()
        await manager.load_plugin(HelloWorldPlugin())
        await manager.load_plugin(SafetyGuardPlugin())

        active = manager.get_active_plugins()
        assert "hello-world" in active
        assert "safety-guard" in active

    @pytest.mark.asyncio
    async def test_get_plugins_by_type(self):
        manager = PluginManager()
        await manager.load_plugin(HelloWorldPlugin())
        await manager.load_plugin(SafetyGuardPlugin())

        tools = manager.get_plugins_by_type(PluginType.TOOL)
        assert len(tools) == 1

    @pytest.mark.asyncio
    async def test_list_plugins(self):
        manager = PluginManager()
        await manager.load_plugin(HelloWorldPlugin())

        plugins = manager.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "hello-world"
        assert plugins[0]["state"] == "active"

    @pytest.mark.asyncio
    async def test_execute_capability(self):
        manager = PluginManager()
        await manager.load_plugin(HelloWorldPlugin())

        result = await manager.execute_capability("hello-world", "greet", {"name": "Test"})
        assert result.success is True
        assert result.output == "Hello, Test!"

    @pytest.mark.asyncio
    async def test_execute_unknown_plugin(self):
        manager = PluginManager()
        result = await manager.execute_capability("nonexistent", "greet")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        manager = PluginManager()
        await manager.load_plugin(HelloWorldPlugin())
        await manager.load_plugin(SafetyGuardPlugin())

        await manager.shutdown_all()
        assert len(manager.get_active_plugins()) == 0

    @pytest.mark.asyncio
    async def test_event_log(self):
        manager = PluginManager()
        await manager.load_plugin(HelloWorldPlugin())

        log = manager.get_event_log()
        assert len(log) >= 1
        assert log[0]["event"] == "loaded"


# ===========================================================================
# Example Plugin Tests
# ===========================================================================


class TestHelloWorldPlugin:
    @pytest.mark.asyncio
    async def test_greet(self):
        plugin = HelloWorldPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        result = await plugin.execute("greet", {"name": "World"}, plugin.context)
        assert result.success is True
        assert result.output == "Hello, World!"

    @pytest.mark.asyncio
    async def test_greet_custom_style(self):
        plugin = HelloWorldPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        result = await plugin.execute("greet", {"name": "Alice", "greeting": "Hi"}, plugin.context)
        assert result.output == "Hi, Alice!"

    @pytest.mark.asyncio
    async def test_count(self):
        plugin = HelloWorldPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        await plugin.execute("greet", {"name": "A"}, plugin.context)
        await plugin.execute("greet", {"name": "B"}, plugin.context)
        result = await plugin.execute("count", {}, plugin.context)
        assert result.output == 2

    @pytest.mark.asyncio
    async def test_unknown_capability(self):
        plugin = HelloWorldPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        result = await plugin.execute("unknown", {}, plugin.context)
        assert result.success is False


class TestSafetyGuardPlugin:
    @pytest.mark.asyncio
    async def test_safe_content(self):
        plugin = SafetyGuardPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        result = await plugin.execute("check_content", {"content": "This is safe"}, plugin.context)
        assert result.success is True
        assert result.output["safe"] is True

    @pytest.mark.asyncio
    async def test_unsafe_content(self):
        plugin = SafetyGuardPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        result = await plugin.execute("check_content", {"content": "This is harmful"}, plugin.context)
        assert result.output["safe"] is False
        assert "harmful" in result.output["violations"]

    @pytest.mark.asyncio
    async def test_add_rule(self):
        plugin = SafetyGuardPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        await plugin.execute("add_rule", {"word": "banned"}, plugin.context)
        result = await plugin.execute("check_content", {"content": "banned word"}, plugin.context)
        assert result.output["safe"] is False


class TestMetricsPlugin:
    @pytest.mark.asyncio
    async def test_record_and_get(self):
        plugin = MetricsPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        await plugin.execute("record_execution", {"duration": 1.5}, plugin.context)
        result = await plugin.execute("get_metrics", {}, plugin.context)
        assert result.output["executions"] == 1
        assert result.output["total_duration"] == 1.5

    @pytest.mark.asyncio
    async def test_reset(self):
        plugin = MetricsPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        await plugin.execute("record_execution", {}, plugin.context)
        await plugin.execute("reset", {}, plugin.context)
        result = await plugin.execute("get_metrics", {}, plugin.context)
        assert result.output["executions"] == 0

    @pytest.mark.asyncio
    async def test_error_counting(self):
        plugin = MetricsPlugin()
        await plugin._do_initialize(PluginContext(plugin_id="test"))

        await plugin.execute("record_execution", {"error": True}, plugin.context)
        result = await plugin.execute("get_metrics", {}, plugin.context)
        assert result.output["errors"] == 1


# ===========================================================================
# Integration Tests
# ===========================================================================


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test a full plugin lifecycle: load, init, execute, unload."""
        manager = PluginManager(harness_config={"env": "test"})

        # Load
        name = await manager.load_plugin(HelloWorldPlugin())
        assert name == "hello-world"

        # Execute
        result = await manager.execute_capability("hello-world", "greet", {"name": "Lifecycle"})
        assert result.success is True
        assert "Lifecycle" in result.output

        # Unload
        await manager.unload_plugin("hello-world")
        assert manager.get_state("hello-world") is None

    @pytest.mark.asyncio
    async def test_hooks_fire_during_lifecycle(self):
        """Test that hooks fire during plugin load/unload."""
        manager = PluginManager()
        events = []

        async def on_load(event):
            events.append(("load", event.data.get("plugin_name")))

        async def on_unload(event):
            events.append(("unload", event.data.get("plugin_name")))

        manager.hooks.register("on_plugin_load", on_load)
        manager.hooks.register("on_plugin_unload", on_unload)

        await manager.load_plugin(HelloWorldPlugin())
        await manager.unload_plugin("hello-world")

        assert ("load", "hello-world") in events
        assert ("unload", "hello-world") in events

    @pytest.mark.asyncio
    async def test_multiple_plugins_with_hooks(self):
        """Test multiple plugins sharing hook events."""
        manager = PluginManager()

        results = []

        async def before_exec(event):
            results.append(event.data.get("plugin_name"))

        manager.hooks.register("on_before_execute", before_exec)

        await manager.load_plugin(HelloWorldPlugin())
        await manager.load_plugin(MetricsPlugin())

        await manager.execute_capability("hello-world", "greet", {"name": "A"})
        await manager.execute_capability("metrics", "reset")

        assert "hello-world" in results
        assert "metrics" in results
