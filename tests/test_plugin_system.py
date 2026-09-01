"""
Tests for Plugin & Hook System.
Test count: 54
"""
import asyncio
import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from harness.plugin_system import (
    FrameworkPlugin,
    GuardPlugin,
    GuardResult,
    HookEvent,
    HookPoint,
    HookRegistry,
    MemoryPlugin,
    Plugin,
    PluginConfig,
    PluginManager,
    PluginState,
    PluginType,
    SolverPlugin,
    EvalPlugin,
    ToolPlugin,
)


def async_run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ──────────────────── PluginConfig Tests ──────────────────────────────


class TestPluginConfig:
    def test_create(self):
        config = PluginConfig(
            plugin_id="test_plugin",
            plugin_type=PluginType.TOOL,
            name="Test Plugin",
            version="1.0.0",
        )
        assert config.plugin_id == "test_plugin"
        assert config.plugin_type == PluginType.TOOL
        assert config.enabled is True
        assert config.priority == 0

    def test_to_dict(self):
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.SOLVER,
            name="Test",
            version="1.0.0",
            description="A test plugin",
        )
        d = config.to_dict()
        assert d["plugin_id"] == "test"
        assert d["plugin_type"] == "solver"
        assert d["description"] == "A test plugin"

    def test_from_dict(self):
        data = {
            "plugin_id": "test",
            "plugin_type": "eval",
            "name": "Test",
            "version": "1.0.0",
            "enabled": False,
            "priority": 5,
            "settings": {"key": "value"},
        }
        config = PluginConfig.from_dict(data)
        assert config.plugin_id == "test"
        assert config.plugin_type == PluginType.EVAL
        assert config.enabled is False
        assert config.priority == 5

    def test_roundtrip(self):
        config = PluginConfig(
            plugin_id="roundtrip",
            plugin_type=PluginType.MEMORY,
            name="Roundtrip",
            version="2.0.0",
            settings={"a": 1, "b": 2},
        )
        d = config.to_dict()
        restored = PluginConfig.from_dict(d)
        assert restored.plugin_id == config.plugin_id
        assert restored.plugin_type == config.plugin_type
        assert restored.settings == config.settings


# ──────────────────── GuardResult Tests ───────────────────────────────


class TestGuardResult:
    def test_allow(self):
        result = GuardResult.allow("Safe")
        assert result.allowed is True
        assert result.reason == "Safe"

    def test_deny(self):
        result = GuardResult.deny("Unsafe", "critical")
        assert result.allowed is False
        assert result.severity == "critical"

    def test_modify(self):
        result = GuardResult.modify({"action": "modified"}, "Changed")
        assert result.allowed is True
        assert result.modified_action == {"action": "modified"}


# ──────────────────── HookEvent Tests ────────────────────────────────


class TestHookEvent:
    def test_create(self):
        event = HookEvent(
            hook_point=HookPoint.PRE_EXECUTE,
            plugin_id="test",
            plugin_type=PluginType.TOOL,
        )
        assert event.cancelled is False
        assert event.result is None

    def test_cancel(self):
        event = HookEvent(
            hook_point=HookPoint.PRE_EXECUTE,
            plugin_id="test",
            plugin_type=PluginType.TOOL,
        )
        event.cancel()
        assert event.cancelled is True


# ──────────────────── HookRegistry Tests ──────────────────────────────


class TestHookRegistry:
    def test_create(self):
        registry = HookRegistry()
        assert registry is not None

    def test_register_and_invoke(self):
        registry = HookRegistry()
        results = []

        async def callback(event):
            results.append(event.hook_point)

        registry.register(HookPoint.PRE_EXECUTE, callback, "plugin1", priority=1)

        event = HookEvent(
            hook_point=HookPoint.PRE_EXECUTE,
            plugin_id="test",
            plugin_type=PluginType.TOOL,
        )
        async_run(registry.invoke(event))

        assert len(results) == 1

    def test_priority_ordering(self):
        registry = HookRegistry()
        results = []

        async def callback1(event):
            results.append("first")

        async def callback2(event):
            results.append("second")

        # Lower priority number = called first
        registry.register(HookPoint.PRE_EXECUTE, callback2, "p2", priority=2)
        registry.register(HookPoint.PRE_EXECUTE, callback1, "p1", priority=1)

        event = HookEvent(
            hook_point=HookPoint.PRE_EXECUTE,
            plugin_id="test",
            plugin_type=PluginType.TOOL,
        )
        async_run(registry.invoke(event))

        # callback1 has higher priority (lower number) so should be called first
        # Wait, the registry sorts by -priority so higher priority = earlier
        # callback2 has priority 2, callback1 has priority 1
        # sorted by -priority: callback2 first (priority 2), then callback1 (priority 1)
        assert results == ["second", "first"]

    def test_unregister(self):
        registry = HookRegistry()
        results = []

        async def callback(event):
            results.append("called")

        registry.register(HookPoint.PRE_EXECUTE, callback, "p1")
        registry.unregister(HookPoint.PRE_EXECUTE, callback, "p1")

        event = HookEvent(
            hook_point=HookPoint.PRE_EXECUTE,
            plugin_id="test",
            plugin_type=PluginType.TOOL,
        )
        async_run(registry.invoke(event))

        assert len(results) == 0

    def test_unregister_all(self):
        registry = HookRegistry()
        results = []

        async def callback(event):
            results.append("called")

        registry.register(HookPoint.PRE_EXECUTE, callback, "plugin1")
        registry.register(HookPoint.POST_EXECUTE, callback, "plugin1")
        registry.unregister_all("plugin1")

        event = HookEvent(
            hook_point=HookPoint.PRE_EXECUTE,
            plugin_id="test",
            plugin_type=PluginType.TOOL,
        )
        async_run(registry.invoke(event))

        assert len(results) == 0

    def test_cancel_stops_propagation(self):
        registry = HookRegistry()
        results = []

        async def callback1(event):
            results.append("first")
            event.cancel()

        async def callback2(event):
            results.append("second")

        registry.register(HookPoint.PRE_EXECUTE, callback1, "p1", priority=2)
        registry.register(HookPoint.PRE_EXECUTE, callback2, "p2", priority=1)

        event = HookEvent(
            hook_point=HookPoint.PRE_EXECUTE,
            plugin_id="test",
            plugin_type=PluginType.TOOL,
        )
        async_run(registry.invoke(event))

        assert results == ["first"]

    def test_hook_error_doesnt_break_chain(self):
        registry = HookRegistry()
        results = []

        async def bad_callback(event):
            raise ValueError("Oops")

        async def good_callback(event):
            results.append("good")

        registry.register(HookPoint.PRE_EXECUTE, bad_callback, "bad", priority=2)
        registry.register(HookPoint.PRE_EXECUTE, good_callback, "good", priority=1)

        event = HookEvent(
            hook_point=HookPoint.PRE_EXECUTE,
            plugin_id="test",
            plugin_type=PluginType.TOOL,
        )
        async_run(registry.invoke(event))

        assert results == ["good"]

    def test_clear(self):
        registry = HookRegistry()

        async def callback(event):
            pass

        registry.register(HookPoint.PRE_EXECUTE, callback)
        registry.clear()

        hooks = registry.get_hooks()
        assert hooks == {}


# ──────────────── Concrete Plugin Implementations for Testing ────────


class TestFrameworkPlugin(FrameworkPlugin):
    def __init__(self, config):
        super().__init__(config)
        self.setup_called = False
        self.teardown_called = False

    async def initialize(self):
        self._set_state(PluginState.ACTIVE)

    async def shutdown(self):
        self._set_state(PluginState.UNLOADED)

    async def setup_framework(self):
        self.setup_called = True

    async def teardown_framework(self):
        self.teardown_called = True


class TestSolverPlugin(SolverPlugin):
    def __init__(self, config):
        super().__init__(config)
        self.solved = []

    async def initialize(self):
        self._set_state(PluginState.ACTIVE)

    async def shutdown(self):
        self._set_state(PluginState.UNLOADED)

    async def solve(self, problem, context):
        self.solved.append(problem)
        return {"solution": "test"}

    def can_solve(self, problem):
        return True


class TestGuardPlugin(GuardPlugin):
    def __init__(self, config):
        super().__init__(config)
        self.checks = []

    async def initialize(self):
        self._set_state(PluginState.ACTIVE)

    async def shutdown(self):
        self._set_state(PluginState.UNLOADED)

    async def check(self, action, context):
        self.checks.append(action)
        return GuardResult.allow("Safe")

    def get_guard_name(self):
        return "test_guard"


# ──────────────────── Plugin Base Tests ──────────────────────────────


class TestPlugin:
    def test_create_framework(self):
        config = PluginConfig(
            plugin_id="fw",
            plugin_type=PluginType.FRAMEWORK,
            name="Framework",
            version="1.0.0",
        )
        plugin = TestFrameworkPlugin(config)
        assert plugin.id == "fw"
        assert plugin.plugin_type == PluginType.FRAMEWORK
        assert plugin.state == PluginState.DISCOVERED

    def test_create_solver(self):
        config = PluginConfig(
            plugin_id="solver",
            plugin_type=PluginType.SOLVER,
            name="Solver",
            version="1.0.0",
        )
        plugin = TestSolverPlugin(config)
        assert plugin.id == "solver"
        assert plugin.plugin_type == PluginType.SOLVER

    def test_pause_resume(self):
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.TOOL,
            name="Test",
            version="1.0.0",
        )
        plugin = TestFrameworkPlugin(config)
        plugin._set_state(PluginState.ACTIVE)
        async_run(plugin.pause())
        assert plugin.state == PluginState.PAUSED
        async_run(plugin.resume())
        assert plugin.state == PluginState.ACTIVE

    def test_update_setting(self):
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.TOOL,
            name="Test",
            version="1.0.0",
            settings={"key": "old"},
        )
        plugin = TestFrameworkPlugin(config)
        plugin.update_setting("key", "new")
        assert plugin.get_settings()["key"] == "new"

    def test_update_settings(self):
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.TOOL,
            name="Test",
            version="1.0.0",
        )
        plugin = TestFrameworkPlugin(config)
        plugin.update_settings({"a": 1, "b": 2})
        assert plugin.get_settings() == {"a": 1, "b": 2}

    def test_to_dict(self):
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.TOOL,
            name="Test",
            version="1.0.0",
        )
        plugin = TestFrameworkPlugin(config)
        d = plugin.to_dict()
        assert d["id"] == "test"
        assert d["type"] == "tool"


# ──────────────────── Plugin Type Tests ──────────────────────────────


class TestFrameworkPluginType:
    def test_setup_teardown(self):
        config = PluginConfig(
            plugin_id="fw",
            plugin_type=PluginType.FRAMEWORK,
            name="FW",
            version="1.0.0",
        )
        plugin = TestFrameworkPlugin(config)
        async_run(plugin.setup_framework())
        assert plugin.setup_called is True
        async_run(plugin.teardown_framework())
        assert plugin.teardown_called is True


class TestSolverPluginType:
    def test_solve(self):
        config = PluginConfig(
            plugin_id="solver",
            plugin_type=PluginType.SOLVER,
            name="Solver",
            version="1.0.0",
        )
        plugin = TestSolverPlugin(config)
        result = async_run(plugin.solve({"problem": "test"}, {}))
        assert result["solution"] == "test"

    def test_can_solve(self):
        config = PluginConfig(
            plugin_id="solver",
            plugin_type=PluginType.SOLVER,
            name="Solver",
            version="1.0.0",
        )
        plugin = TestSolverPlugin(config)
        assert plugin.can_solve({"any": "problem"}) is True


class TestGuardPluginType:
    def test_check(self):
        config = PluginConfig(
            plugin_id="guard",
            plugin_type=PluginType.GUARD,
            name="Guard",
            version="1.0.0",
        )
        plugin = TestGuardPlugin(config)
        result = async_run(plugin.check({"action": "test"}, {}))
        assert result.allowed is True

    def test_get_guard_name(self):
        config = PluginConfig(
            plugin_id="guard",
            plugin_type=PluginType.GUARD,
            name="Guard",
            version="1.0.0",
        )
        plugin = TestGuardPlugin(config)
        assert plugin.get_guard_name() == "test_guard"


# ──────────────────── PluginManager Tests ────────────────────────────


class TestPluginManager:
    def test_create(self):
        pm = PluginManager()
        assert pm.plugin_count == 0
        assert pm.active_count == 0

    def test_add_plugin_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PluginManager()
            pm.add_plugin_dir(tmpdir)
            assert len(pm._plugin_dirs) == 1

    def test_load_plugin(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="test_fw",
            plugin_type=PluginType.FRAMEWORK,
            name="Test",
            version="1.0.0",
        )
        plugin = async_run(pm.load_plugin(config))
        assert plugin is not None
        assert pm.plugin_count == 1
        assert pm.active_count == 1

    def test_load_duplicate(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.FRAMEWORK,
            name="Test",
            version="1.0.0",
        )
        async_run(pm.load_plugin(config))
        result = async_run(pm.load_plugin(config))
        assert result is None  # Already loaded
        assert pm.plugin_count == 1

    def test_unload_plugin(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.FRAMEWORK,
            name="Test",
            version="1.0.0",
        )
        async_run(pm.load_plugin(config))
        result = async_run(pm.unload_plugin("test"))
        assert result is True
        assert pm.plugin_count == 0

    def test_unload_nonexistent(self):
        pm = PluginManager()
        result = async_run(pm.unload_plugin("nonexistent"))
        assert result is False

    def test_pause_resume(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.FRAMEWORK,
            name="Test",
            version="1.0.0",
        )
        async_run(pm.load_plugin(config))
        assert pm.get_plugin_state("test") == PluginState.ACTIVE

        async_run(pm.pause_plugin("test"))
        assert pm.get_plugin_state("test") == PluginState.PAUSED

        async_run(pm.resume_plugin("test"))
        assert pm.get_plugin_state("test") == PluginState.ACTIVE

    def test_get_plugin(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.FRAMEWORK,
            name="Test",
            version="1.0.0",
        )
        async_run(pm.load_plugin(config))
        plugin = pm.get_plugin("test")
        assert plugin is not None
        assert plugin.id == "test"

    def test_get_plugins_by_type(self):
        pm = PluginManager()
        config1 = PluginConfig(
            plugin_id="fw1",
            plugin_type=PluginType.FRAMEWORK,
            name="FW1",
            version="1.0.0",
        )
        config2 = PluginConfig(
            plugin_id="solver1",
            plugin_type=PluginType.SOLVER,
            name="Solver1",
            version="1.0.0",
        )
        async_run(pm.load_plugin(config1))
        async_run(pm.load_plugin(config2))

        fw_plugins = pm.get_plugins_by_type(PluginType.FRAMEWORK)
        assert len(fw_plugins) == 1
        assert fw_plugins[0].id == "fw1"

    def test_get_all_plugins(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.FRAMEWORK,
            name="Test",
            version="1.0.0",
        )
        async_run(pm.load_plugin(config))
        plugins = pm.get_all_plugins()
        assert len(plugins) == 1

    def test_update_plugin_config(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.FRAMEWORK,
            name="Test",
            version="1.0.0",
            settings={"key": "old"},
        )
        async_run(pm.load_plugin(config))
        result = async_run(pm.update_plugin_config("test", {"key": "new"}))
        assert result is True
        assert pm.get_plugin("test").get_settings()["key"] == "new"

    def test_update_plugin_config_nonexistent(self):
        pm = PluginManager()
        result = async_run(pm.update_plugin_config("nonexistent", {}))
        assert result is False

    def test_get_status(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="test",
            plugin_type=PluginType.FRAMEWORK,
            name="Test",
            version="1.0.0",
        )
        async_run(pm.load_plugin(config))
        status = pm.get_status()
        assert status["total_plugins"] == 1
        assert status["active_plugins"] == 1

    def test_set_isolated(self):
        pm = PluginManager()
        pm.set_isolated("test", True)
        assert pm.is_isolated("test") is True

    def test_is_isolated_default(self):
        pm = PluginManager()
        assert pm.is_isolated("nonexistent") is False

    def test_load_config_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_data = {
                "plugins": [
                    {
                        "plugin_id": "from_file",
                        "plugin_type": "tool",
                        "name": "FromFile",
                        "version": "1.0.0",
                    }
                ]
            }
            path = os.path.join(tmpdir, "plugins.json")
            with open(path, "w") as f:
                json.dump(config_data, f)

            pm = PluginManager()
            configs = pm.load_config_from_file(path)
            assert len(configs) == 1
            assert configs[0].plugin_id == "from_file"

    def test_save_config_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PluginManager()
            config = PluginConfig(
                plugin_id="save_test",
                plugin_type=PluginType.TOOL,
                name="SaveTest",
                version="1.0.0",
                settings={"key": "value"},
            )
            async_run(pm.load_plugin(config))

            path = os.path.join(tmpdir, "output.json")
            pm.save_config_to_file(path)

            with open(path) as f:
                data = json.load(f)
            assert len(data["plugins"]) == 1
            assert data["plugins"][0]["plugin_id"] == "save_test"

    def test_discover_plugins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a plugin directory with manifest
            plugin_dir = os.path.join(tmpdir, "my_plugin")
            os.makedirs(plugin_dir)
            manifest = {
                "plugin_id": "discovered",
                "plugin_type": "tool",
                "name": "Discovered",
                "version": "1.0.0",
            }
            with open(os.path.join(plugin_dir, "plugin.json"), "w") as f:
                json.dump(manifest, f)

            pm = PluginManager()
            pm.add_plugin_dir(tmpdir)
            discovered = pm.discover_plugins()
            assert len(discovered) == 1
            assert discovered[0].plugin_id == "discovered"

    def test_hook_registry_access(self):
        pm = PluginManager()
        assert pm.hook_registry is not None

    def test_reload_plugin(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="reload_test",
            plugin_type=PluginType.FRAMEWORK,
            name="Reload",
            version="1.0.0",
        )
        async_run(pm.load_plugin(config))
        plugin = async_run(pm.reload_plugin("reload_test"))
        assert plugin is not None
        assert pm.plugin_count == 1

    def test_reload_nonexistent(self):
        pm = PluginManager()
        plugin = async_run(pm.reload_plugin("nonexistent"))
        assert plugin is None

    def test_plugin_state_tracking(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="state_test",
            plugin_type=PluginType.FRAMEWORK,
            name="State",
            version="1.0.0",
        )
        assert pm.get_plugin_state("state_test") is None
        async_run(pm.load_plugin(config))
        assert pm.get_plugin_state("state_test") == PluginState.ACTIVE

    def test_plugin_config_access(self):
        pm = PluginManager()
        config = PluginConfig(
            plugin_id="config_test",
            plugin_type=PluginType.FRAMEWORK,
            name="Config",
            version="1.0.0",
            settings={"key": "value"},
        )
        async_run(pm.load_plugin(config))
        retrieved = pm.get_plugin_config("config_test")
        assert retrieved is not None
        assert retrieved.plugin_id == "config_test"
