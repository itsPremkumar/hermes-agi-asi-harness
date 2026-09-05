"""Tests for tools/ — Tool Registry."""

from __future__ import annotations

import pytest

from src.harness.errors import RateLimitError, ToolError
from src.harness.tools import RateLimiter, Tool, ToolRegistry, ToolSchema


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_allows_within_limit(self):
        rl = RateLimiter(max_calls=5, period=60.0)
        for _ in range(5):
            assert rl.allow()

    def test_blocks_after_limit(self):
        rl = RateLimiter(max_calls=2, period=60.0)
        assert rl.allow()
        assert rl.allow()
        assert not rl.allow()

    def test_remaining_count(self):
        rl = RateLimiter(max_calls=5, period=60.0)
        rl.allow()
        rl.allow()
        assert rl.remaining == 3


class TestToolSchema:
    """Tests for ToolSchema."""

    def test_validates_required_params(self):
        schema = ToolSchema(
            properties={"name": {"type": "string"}},
            required=["name"],
        )
        errors = schema.validate({"name": "test"})
        assert errors == []

    def test_missing_required_param(self):
        schema = ToolSchema(
            properties={"name": {"type": "string"}},
            required=["name"],
        )
        errors = schema.validate({})
        assert len(errors) == 1

    def test_type_validation(self):
        schema = ToolSchema(
            properties={"count": {"type": "number"}},
            required=[],
        )
        errors = schema.validate({"count": "not a number"})
        assert len(errors) == 1

    def test_type_validation_passes(self):
        schema = ToolSchema(
            properties={"count": {"type": "number"}},
            required=[],
        )
        errors = schema.validate({"count": 42})
        assert errors == []


class TestTool:
    """Tests for Tool."""

    def test_invoke_success(self):
        schema = ToolSchema(properties={"x": {"type": "number"}}, required=["x"])
        tool = Tool("add", "Add numbers", lambda x: x + 1, schema)
        result = tool.invoke(x=5)
        assert result == 6

    def test_invoke_validation_error(self):
        schema = ToolSchema(properties={"x": {"type": "number"}}, required=["x"])
        tool = Tool("add", "Add", lambda x: x, schema)
        with pytest.raises(ToolError):
            tool.invoke(x="not a number")

    def test_to_schema(self):
        schema = ToolSchema(properties={"x": {"type": "number"}}, required=["x"])
        tool = Tool("add", "Add", lambda x: x, schema)
        s = tool.to_schema()
        assert s["name"] == "add"
        assert "parameters" in s


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_get(self):
        reg = ToolRegistry()
        reg.register("echo", "Echo input", lambda x: x, {"x": {"type": "string"}}, ["x"])
        tool = reg.get("echo")
        assert tool is not None
        assert tool.name == "echo"

    def test_invoke(self):
        reg = ToolRegistry()
        reg.register("double", "Double a number", lambda n: n * 2, {"n": {"type": "number"}}, ["n"])
        result = reg.invoke("double", n=5)
        assert result == 10

    def test_invoke_unknown_tool(self):
        reg = ToolRegistry()
        with pytest.raises(ToolError):
            reg.invoke("missing")

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register("t1", "Tool 1", lambda: None, {}, [])
        reg.register("t2", "Tool 2", lambda: None, {}, [])
        tools = reg.list_tools()
        assert len(tools) == 2

    def test_unregister(self):
        reg = ToolRegistry()
        reg.register("t1", "Tool 1", lambda: None, {}, [])
        assert reg.unregister("t1") is True
        assert reg.get("t1") is None

    def test_count(self):
        reg = ToolRegistry()
        reg.register("t1", "Tool 1", lambda: None, {}, [])
        assert reg.count == 1

    def test_clear(self):
        reg = ToolRegistry()
        reg.register("t1", "Tool 1", lambda: None, {}, [])
        reg.clear()
        assert reg.count == 0

    def test_overwrite_warning(self):
        reg = ToolRegistry()
        reg.register("t1", "Tool 1", lambda: None, {}, [])
        reg.register("t1", "Tool 1 v2", lambda: None, {}, [])
        assert reg.count == 1

    def test_rate_limiting(self):
        reg = ToolRegistry()
        reg.register(
            "limited",
            "Rate limited",
            lambda: "ok",
            {},
            [],
            rate_limit=(1, 60.0),
        )
        reg.invoke("limited")
        with pytest.raises(RateLimitError):
            reg.invoke("limited")

    def test_call_count_tracking(self):
        reg = ToolRegistry()
        reg.register("t1", "Tool 1", lambda: None, {}, [])
        reg.invoke("t1")
        reg.invoke("t1")
        assert reg.get("t1").call_count == 2
