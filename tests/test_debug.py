"""Tests for Debug Engine."""
import pytest

from core.debug import BugReport, DebugEngine


class TestDebugEngine:
    def test_create(self):
        engine = DebugEngine()
        assert engine._bugs == {}

    @pytest.mark.asyncio
    async def test_reproduce(self):
        engine = DebugEngine()
        bug = await engine.reproduce("NameError: name 'x' is not defined", "main.py")
        assert isinstance(bug, BugReport)
        assert bug.file_path == "main.py"
        assert bug.bug_id in engine._bugs

    @pytest.mark.asyncio
    async def test_analyze_root_cause_name_error(self):
        engine = DebugEngine()
        bug = await engine.reproduce("NameError: name 'x' is not defined", "main.py")
        result = await engine.analyze_root_cause(bug.bug_id)
        assert result["root_cause"] == "Missing variable or import"

    @pytest.mark.asyncio
    async def test_analyze_root_cause_type_error(self):
        engine = DebugEngine()
        bug = await engine.reproduce("TypeError: cannot concatenate", "main.py")
        result = await engine.analyze_root_cause(bug.bug_id)
        assert result["root_cause"] == "Type mismatch"

    @pytest.mark.asyncio
    async def test_analyze_root_cause_index_error(self):
        engine = DebugEngine()
        bug = await engine.reproduce("IndexError: list index out of range", "main.py")
        result = await engine.analyze_root_cause(bug.bug_id)
        assert result["root_cause"] == "Index out of bounds"

    @pytest.mark.asyncio
    async def test_analyze_root_cause_key_error(self):
        engine = DebugEngine()
        bug = await engine.reproduce("KeyError: 'missing_key'", "main.py")
        result = await engine.analyze_root_cause(bug.bug_id)
        assert result["root_cause"] == "Missing dictionary key"

    @pytest.mark.asyncio
    async def test_analyze_root_cause_unknown(self):
        engine = DebugEngine()
        bug = await engine.reproduce("Something went wrong", "main.py")
        result = await engine.analyze_root_cause(bug.bug_id)
        assert result["root_cause"] == "Unknown"

    @pytest.mark.asyncio
    async def test_analyze_not_found(self):
        engine = DebugEngine()
        result = await engine.analyze_root_cause("nonexistent")
        assert "error" in result

    def test_extract_line_number(self):
        engine = DebugEngine()
        line = engine._extract_line_number("Error at line 42")
        assert line == 42

    def test_extract_line_number_missing(self):
        engine = DebugEngine()
        line = engine._extract_line_number("Error occurred")
        assert line == 0

    @pytest.mark.asyncio
    async def test_health(self):
        engine = DebugEngine()
        health = await engine.health()
        assert health["status"] == "healthy"
