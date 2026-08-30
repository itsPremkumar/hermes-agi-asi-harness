"""
Tests for the dynamic configuration system.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from harness.config import Config, ConfigChangeEvent


class TestConfig:
    def test_get_set(self):
        config = Config()
        asyncio.run(config.set("key", "value"))
        assert config.get("key") == "value"

    def test_get_default(self):
        config = Config()
        assert config.get("missing", "default") == "default"

    def test_nested_keys(self):
        config = Config()
        asyncio.run(config.set("database.host", "localhost"))
        asyncio.run(config.set("database.port", 5432))
        assert config.get("database.host") == "localhost"
        assert config.get("database.port") == 5432

    def test_has(self):
        config = Config()
        asyncio.run(config.set("key", "value"))
        assert config.has("key") is True
        assert config.has("missing") is False

    def test_delete(self):
        config = Config()
        asyncio.run(config.set("key", "value"))
        result = asyncio.run(config.delete("key"))
        assert result is True
        assert config.has("key") is False

    def test_load_json_file(self):
        config = Config()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"name": "test", "version": "1.0"}, f)
            f.flush()
            asyncio.run(config.load_file(f.name))

        assert config.get("name") == "test"
        assert config.get("version") == "1.0"
        os.unlink(f.name)

    def test_load_file_not_found(self):
        config = Config()
        with pytest.raises(FileNotFoundError):
            asyncio.run(config.load_file("/nonexistent/path.json"))

    @pytest.mark.asyncio
    async def test_subscribe(self):
        config = Config()
        changes = []

        async def on_change(key, old, new):
            changes.append((key, old, new))

        config.subscribe(on_change)
        await config.set("key", "value")

        assert len(changes) == 1
        assert changes[0] == ("key", None, "value")

    def test_unsubscribe(self):
        config = Config()
        changes = []

        async def on_change(key, old, new):
            changes.append((key, old, new))

        unsub = config.subscribe(on_change)
        asyncio.run(config.set("key1", "a"))
        unsub()
        asyncio.run(config.set("key2", "b"))

        assert len(changes) == 1

    def test_snapshot_and_restore(self):
        config = Config()
        asyncio.run(config.set("key", "value"))
        snapshot = config.snapshot()

        asyncio.run(config.set("key", "changed"))
        assert config.get("key") == "changed"

        asyncio.run(config.restore(snapshot))
        assert config.get("key") == "value"

    def test_merge(self):
        config = Config()
        asyncio.run(config.set("a", 1))
        asyncio.run(config.merge({"b": 2, "c": 3}))

        assert config.get("a") == 1
        assert config.get("b") == 2
        assert config.get("c") == 3

    def test_deep_merge(self):
        config = Config()
        asyncio.run(config.set("db", {"host": "localhost", "port": 5432}))
        asyncio.run(config.merge({"db": {"port": 3306, "name": "test"}}))

        assert config.get("db.host") == "localhost"
        assert config.get("db.port") == 3306
        assert config.get("db.name") == "test"

    def test_change_log(self):
        config = Config()
        asyncio.run(config.set("a", 1))
        asyncio.run(config.set("a", 2))
        asyncio.run(config.set("b", 3))

        log = config.get_change_log()
        assert len(log) == 3
        assert isinstance(log[0], ConfigChangeEvent)

    def test_data_isolation(self):
        config = Config()
        asyncio.run(config.set("key", "original"))
        data = config.data
        data["key"] = "modified"
        assert config.get("key") == "original"

    def test_load_env(self):
        config = Config(env_prefix="TEST_")
        os.environ["TEST_FOO"] = "bar"
        os.environ["TEST_NESTED__KEY"] = "value"

        count = asyncio.run(config.load_env())

        assert count == 2
        assert config.get("foo") == "bar"
        assert config.get("nested.key") == "value"

        del os.environ["TEST_FOO"]
        del os.environ["TEST_NESTED__KEY"]

    def test_repr(self):
        config = Config()
        asyncio.run(config.set("a", 1))
        assert "Config" in repr(config)
        assert "keys=1" in repr(config)
