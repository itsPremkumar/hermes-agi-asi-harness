"""Tests for ConfigManager."""
import json
import os
import tempfile
import time

import pytest

from src.harness.runtime.config_manager import ConfigManager


class TestConfigManager:
    def test_init_empty(self):
        cm = ConfigManager()
        assert cm.get_all() == {}

    def test_init_with_config(self):
        cm = ConfigManager({"key": "value"})
        assert cm.get("key") == "value"

    def test_get_set_basic(self):
        cm = ConfigManager()
        cm.set("name", "test")
        assert cm.get("name") == "test"

    def test_get_with_default(self):
        cm = ConfigManager()
        assert cm.get("missing", default="fallback") == "fallback"

    def test_get_without_default_returns_none(self):
        cm = ConfigManager()
        assert cm.get("missing") is None

    def test_dot_notation_get(self):
        cm = ConfigManager({"a": {"b": {"c": "deep"}}})
        assert cm.get("a.b.c") == "deep"

    def test_dot_notation_set(self):
        cm = ConfigManager()
        cm.set("a.b.c", "value")
        assert cm.get("a.b.c") == "value"
        assert cm.get("a") == {"b": {"c": "value"}}

    def test_dot_notation_set_existing(self):
        cm = ConfigManager({"a": {"b": "old"}})
        cm.set("a.c", "new")
        assert cm.get("a.b") == "old"
        assert cm.get("a.c") == "new"

    def test_has_existing(self):
        cm = ConfigManager({"key": "value"})
        assert cm.has("key") is True

    def test_has_missing(self):
        cm = ConfigManager()
        assert cm.has("missing") is False

    def test_has_dot_notation(self):
        cm = ConfigManager({"a": {"b": "value"}})
        assert cm.has("a.b") is True
        assert cm.has("a.missing") is False

    def test_delete_existing(self):
        cm = ConfigManager({"key": "value"})
        assert cm.delete("key") is True
        assert cm.has("key") is False

    def test_delete_missing(self):
        cm = ConfigManager()
        assert cm.delete("missing") is False

    def test_delete_returns_old_value(self):
        cm = ConfigManager({"key": "value"})
        assert cm.delete("key") is True

    def test_load_dict_merge(self):
        cm = ConfigManager({"a": 1})
        cm.load_dict({"b": 2}, merge=True)
        assert cm.get("a") == 1
        assert cm.get("b") == 2

    def test_load_dict_no_merge(self):
        cm = ConfigManager({"a": 1})
        cm.load_dict({"b": 2}, merge=False)
        assert cm.get("a") is None
        assert cm.get("b") == 2

    def test_load_dict_deep_merge(self):
        cm = ConfigManager({"a": {"b": 1}})
        cm.load_dict({"a": {"c": 2}}, merge=True)
        assert cm.get("a.b") == 1
        assert cm.get("a.c") == 2

    def test_load_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            f.flush()
            cm = ConfigManager()
            cm.load_json(f.name)
            assert cm.get("key") == "value"
        os.unlink(f.name)

    def test_load_env(self):
        os.environ["HARNESS_TEST_KEY"] = "env_value"
        cm = ConfigManager()
        cm.load_env(prefix="HARNESS_")
        assert cm.get("test.key") == "env_value"
        del os.environ["HARNESS_TEST_KEY"]

    def test_load_env_json_value(self):
        os.environ["HARNESS_TEST_JSON"] = '{"nested": true}'
        cm = ConfigManager()
        cm.load_env(prefix="HARNESS_")
        assert cm.get("test.json") == {"nested": True}
        del os.environ["HARNESS_TEST_JSON"]

    def test_get_all_returns_copy(self):
        cm = ConfigManager({"key": "value"})
        all_config = cm.get_all()
        all_config["key"] = "modified"
        assert cm.get("key") == "value"

    def test_set_default(self):
        cm = ConfigManager()
        cm.set_default("key", "default")
        assert cm.get("key") == "default"

    def test_set_overrides_default(self):
        cm = ConfigManager()
        cm.set_default("key", "default")
        cm.set("key", "custom")
        assert cm.get("key") == "custom"

    def test_on_change_callback(self):
        changes = []
        cm = ConfigManager()
        cm.on_change(lambda key, old, new: changes.append((key, old, new)))
        cm.set("key", "value")
        assert len(changes) == 1
        assert changes[0] == ("key", None, "value")

    def test_on_change_callback_update(self):
        changes = []
        cm = ConfigManager({"key": "old"})
        cm.on_change(lambda key, old, new: changes.append((key, old, new)))
        cm.set("key", "new")
        assert changes[0] == ("key", "old", "new")

    def test_reset(self):
        cm = ConfigManager({"key": "value"})
        cm.reset()
        assert cm.get_all() == {}

    def test_deep_copy_on_set(self):
        cm = ConfigManager()
        data = {"nested": [1, 2, 3]}
        cm.set("key", data)
        data["nested"].append(4)
        assert cm.get("key") == {"nested": [1, 2, 3]}

    def test_deep_copy_on_get(self):
        cm = ConfigManager({"key": {"nested": [1, 2, 3]}})
        data = cm.get("key")
        data["nested"].append(4)
        assert cm.get("key") == {"nested": [1, 2, 3]}

    def test_watcher_reload(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": 1}, f)
            f.flush()
            fname = f.name

        cm = ConfigManager()
        cm.load_json(fname)
        assert cm.get("version") == 1

        cm.start_watcher(fname, interval=0.1)
        time.sleep(0.2)

        with open(fname, "w") as f:
            json.dump({"version": 2}, f)

        time.sleep(0.5)
        assert cm.get("version") == 2
        cm.stop_watcher()
        os.unlink(fname)

    def test_stop_watcher(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            f.flush()
            fname = f.name

        cm = ConfigManager()
        cm.start_watcher(fname)
        cm.stop_watcher()
        os.unlink(fname)
