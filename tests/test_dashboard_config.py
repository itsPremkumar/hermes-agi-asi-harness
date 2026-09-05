"""Tests for ConfigEditor."""
import pytest

from core.dashboard.config import ConfigEditor, ConfigScope, ConfigValidationError


class TestConfigEditor:
    def test_create(self):
        ce = ConfigEditor()
        assert ce.count() == 0

    def test_set(self):
        ce = ConfigEditor()
        item = ce.set("key1", "value1")
        assert item.key == "key1"
        assert item.value == "value1"
        assert ce.count() == 1

    def test_get(self):
        ce = ConfigEditor()
        ce.set("key1", "value1")
        item = ce.get("key1")
        assert item is not None
        assert item.value == "value1"

    def test_get_value(self):
        ce = ConfigEditor()
        ce.set("key1", 42)
        assert ce.get_value("key1") == 42

    def test_get_value_default(self):
        ce = ConfigEditor()
        assert ce.get_value("missing", "default") == "default"

    def test_remove(self):
        ce = ConfigEditor()
        ce.set("key1", "value1")
        assert ce.remove("key1") is True
        assert ce.count() == 0

    def test_list_all(self):
        ce = ConfigEditor()
        ce.set("a", 1)
        ce.set("b", 2)
        assert len(ce.list_all()) == 2

    def test_list_by_scope(self):
        ce = ConfigEditor()
        ce.set("a", 1, scope=ConfigScope.GLOBAL)
        ce.set("b", 2, scope=ConfigScope.USER)
        assert len(ce.list_by_scope(ConfigScope.GLOBAL)) == 1

    def test_register_validator(self):
        ce = ConfigEditor()
        ce.register_validator("port", lambda v: isinstance(v, int) and 0 < v < 65536)
        ce.set("port", 8080)
        assert ce.get_value("port") == 8080

    def test_validator_rejects(self):
        ce = ConfigEditor()
        ce.register_validator("port", lambda v: isinstance(v, int))
        with pytest.raises(ConfigValidationError):
            ce.set("port", "not_a_number")

    def test_get_history(self):
        ce = ConfigEditor()
        ce.set("key1", "v1")
        ce.set("key1", "v2")
        history = ce.get_history()
        assert len(history) == 2

    def test_get_state(self):
        ce = ConfigEditor()
        ce.set("a", 1, scope=ConfigScope.GLOBAL)
        state = ce.get_state()
        assert state["total"] == 1
        assert state["global"] == 1
