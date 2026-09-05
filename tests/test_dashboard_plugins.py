"""Tests for PluginManager."""
from core.dashboard.plugins import PluginManager, PluginStatus


class TestPluginManager:
    def test_create(self):
        pm = PluginManager()
        assert pm.count() == 0

    def test_register(self):
        pm = PluginManager()
        p = pm.register("test", "1.0", "Test plugin")
        assert p.name == "test"
        assert p.version == "1.0"
        assert p.status == PluginStatus.ACTIVE
        assert pm.count() == 1

    def test_register_with_capabilities(self):
        pm = PluginManager()
        p = pm.register("test", capabilities=["search", "browse"])
        assert "search" in p.capabilities

    def test_unregister(self):
        pm = PluginManager()
        p = pm.register("test")
        assert pm.unregister(p.id) is True
        assert pm.count() == 0

    def test_unregister_missing(self):
        pm = PluginManager()
        assert pm.unregister("nonexistent") is False

    def test_get(self):
        pm = PluginManager()
        p = pm.register("test")
        result = pm.get(p.id)
        assert result is not None
        assert result.name == "test"

    def test_list_all(self):
        pm = PluginManager()
        pm.register("a")
        pm.register("b")
        assert len(pm.list_all()) == 2

    def test_list_active(self):
        pm = PluginManager()
        pm.register("a")
        pm.register("b")
        assert len(pm.list_active()) == 2

    def test_enable(self):
        pm = PluginManager()
        p = pm.register("test")
        pm.disable(p.id)
        assert pm.enable(p.id) is True
        assert pm.get(p.id).status == PluginStatus.ACTIVE

    def test_disable(self):
        pm = PluginManager()
        p = pm.register("test")
        assert pm.disable(p.id) is True
        assert pm.get(p.id).status == PluginStatus.DISABLED

    def test_set_error(self):
        pm = PluginManager()
        p = pm.register("test")
        assert pm.set_error(p.id) is True
        assert pm.get(p.id).status == PluginStatus.ERROR

    def test_active_count(self):
        pm = PluginManager()
        p1 = pm.register("a")
        pm.register("b")
        pm.disable(p1.id)
        assert pm.active_count() == 1

    def test_search(self):
        pm = PluginManager()
        pm.register("web-search", description="Search the web")
        pm.register("code-gen", description="Generate code")
        results = pm.search("search")
        assert len(results) == 1

    def test_get_state(self):
        pm = PluginManager()
        pm.register("a")
        pm.register("b")
        state = pm.get_state()
        assert state["total"] == 2
        assert state["active"] == 2
