"""Fuzzing engine for MCP message handling."""

from __future__ import annotations

import asyncio
import random
import string
import time
from typing import Any, Callable, Optional

from mcptest.config import Config
from mcptest.models import (
    FuzzResult,
    TestResult,
    TestStatus,
    TestSuite,
)
from mcptest.client import MockMCPClient


def _fuzz_string(max_len: int = 100) -> str:
    """Generate a random fuzzed string."""
    strategies = [
        lambda: "",
        lambda: "A" * 10000,
        lambda: "".join(chr(c) for c in range(1, 32)),
        lambda: "' OR 1=1 --",
        lambda: "<script>alert(1)</script>",
        lambda: "../../../etc/passwd",
        lambda: "$(whoami)",
        lambda: "\x00\x08\x10",
        lambda: "\x00" * 50,
        lambda: " ".join(random.choices(string.ascii_letters, k=random.randint(0, 50))),
    ]
    return random.choice(strategies)()


def _fuzz_number() -> float | int:
    """Generate a random fuzzed number."""
    strategies = [
        lambda: 0,
        lambda: -1,
        lambda: 2**63 - 1,
        lambda: -(2**63),
        lambda: float("inf"),
        lambda: float("-inf"),
        lambda: float("nan"),
        lambda: random.random() * 1e10,
        lambda: random.randint(-1000, 1000),
    ]
    return random.choice(strategies)()


def _fuzz_type() -> Any:
    """Generate a random fuzzed value of any type."""
    strategies = [
        lambda: None,
        lambda: True,
        lambda: False,
        lambda: _fuzz_string(),
        lambda: _fuzz_number(),
        lambda: [],
        lambda: {},
        lambda: [_fuzz_string() for _ in range(random.randint(0, 5))],
        lambda: {f"key{i}": _fuzz_string() for i in range(random.randint(0, 5))},
    ]
    return random.choice(strategies)()


def _mutate_jsonrpc(msg: dict[str, Any]) -> dict[str, Any]:
    """Mutate a JSON-RPC message with fuzzed values."""
    mutated = dict(msg)
    if random.random() < 0.3:
        mutated["method"] = _fuzz_string()
    if random.random() < 0.3 and "params" in mutated:
        if isinstance(mutated["params"], dict):
            key = random.choice(list(mutated["params"].keys())) if mutated["params"] else "fuzz"
            mutated["params"][key] = _fuzz_type()
        else:
            mutated["params"] = _fuzz_type()
    if random.random() < 0.1:
        mutated["jsonrpc"] = _fuzz_string()
    if random.random() < 0.1:
        del mutated["id"]
    return mutated


class FuzzingEngine:
    """Fuzzes MCP server message handling."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = MockMCPClient(config)
        self.iterations = config.fuzzing_iterations
        self._crash_count = 0
        self._unique_error_codes: set[int] = set()
        self._paths_covered: set[str] = set()

    async def run(self) -> FuzzResult:
        """Execute the fuzzing campaign."""
        suite = TestSuite(name="MCP Fuzzing")

        tests = [
            self._test_method_fuzzing,
            self._test_param_fuzzing,
            self._test_type_confusion,
            self._test_missing_fields,
            self._test_extra_fields,
            self._test_boundary_values,
            self._test_null_bytes,
            self._test_encoding_issues,
        ]

        for test_fn in tests:
            result = await test_fn()
            suite.results.append(result)

        suite.finished_at = __import__("datetime").datetime.utcnow()

        coverage = len(self._paths_covered) / max(len(self._unique_error_codes) + len(self._paths_covered), 1) * 100

        return FuzzResult(
            suite=suite,
            iterations=self.iterations,
            crashes=self._crash_count,
            unique_paths=len(self._paths_covered),
            coverage_pct=min(coverage, 100.0),
        )

    async def _fuzz_round(self, label: str, mutate_fn: Callable[[], dict[str, Any]]) -> TestResult:
        """Run a round of fuzzing mutations."""
        start = time.monotonic()
        crashes = 0
        try:
            for _ in range(self.iterations // 8):
                msg = mutate_fn()
                try:
                    resp = await self.client.send_raw(msg)
                    if "error" in resp:
                        code = resp["error"].get("code", 0)
                        self._unique_error_codes.add(code)
                        self._paths_covered.add(f"error:{code}")
                except (ConnectionError, OSError, asyncio.TimeoutError):
                    crashes += 1
                    self._crash_count += 1
                    self._paths_covered.add("crash")
                except Exception:
                    self._paths_covered.add("exception")

            duration = (time.monotonic() - start) * 1000
            if crashes > 0:
                return TestResult(
                    name=label,
                    status=TestStatus.FAIL,
                    duration_ms=duration,
                    message=f"{crashes} crashes detected",
                    details={"crashes": crashes},
                )
            return TestResult(
                name=label,
                status=TestStatus.PASS,
                duration_ms=duration,
                message=f"No crashes, {len(self._unique_error_codes)} unique error codes",
                details={"unique_errors": len(self._unique_error_codes)},
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name=label,
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_method_fuzzing(self) -> TestResult:
        """Fuzz the method field."""
        base = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        return await self._fuzz_round("method_fuzzing", lambda: _mutate_jsonrpc(base))

    async def _test_param_fuzzing(self) -> TestResult:
        """Fuzz parameter values."""
        base = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "echo", "arguments": {}}}
        return await self._fuzz_round("param_fuzzing", lambda: _mutate_jsonrpc(base))

    async def _test_type_confusion(self) -> TestResult:
        """Test type confusion attacks."""
        start = time.monotonic()
        cases = [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": 123, "arguments": "not_a_dict"}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "echo", "arguments": [1, 2, 3]}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": "string_instead_of_object"},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": [1, 2]},
        ]
        crashes = 0
        for msg in cases:
            try:
                await self.client.send_raw(msg)
            except (ConnectionError, OSError):
                crashes += 1
                self._crash_count += 1
            except Exception:
                pass
        duration = (time.monotonic() - start) * 1000
        if crashes > 0:
            return TestResult(
                name="type_confusion",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message=f"{crashes} crashes from type confusion",
            )
        return TestResult(
            name="type_confusion",
            status=TestStatus.PASS,
            duration_ms=duration,
            message="Server handled type confusion gracefully",
        )

    async def _test_missing_fields(self) -> TestResult:
        """Test with missing required fields."""
        start = time.monotonic()
        cases = [
            {"id": 1, "method": "tools/list"},
            {"jsonrpc": "2.0", "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 1},
        ]
        crashes = 0
        for msg in cases:
            try:
                await self.client.send_raw(msg)
            except (ConnectionError, OSError):
                crashes += 1
                self._crash_count += 1
            except Exception:
                pass
        duration = (time.monotonic() - start) * 1000
        if crashes > 0:
            return TestResult(
                name="missing_fields",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message=f"{crashes} crashes from missing fields",
            )
        return TestResult(
            name="missing_fields",
            status=TestStatus.PASS,
            duration_ms=duration,
            message="Server handled missing fields gracefully",
        )

    async def _test_extra_fields(self) -> TestResult:
        """Test with extra unexpected fields."""
        start = time.monotonic()
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
            "extra_field": "unexpected",
            "another": 12345,
        }
        try:
            await self.client.send_raw(msg)
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="extra_fields",
                status=TestStatus.PASS,
                duration_ms=duration,
                message="Server ignored extra fields",
            )
        except (ConnectionError, OSError):
            duration = (time.monotonic() - start) * 1000
            self._crash_count += 1
            return TestResult(
                name="extra_fields",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Server crashed on extra fields",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="extra_fields",
                status=TestStatus.PASS,
                duration_ms=duration,
                message=f"Server rejected extra fields: {type(e).__name__}",
            )

    async def _test_boundary_values(self) -> TestResult:
        """Test boundary values."""
        start = time.monotonic()
        cases = [
            {"jsonrpc": "2.0", "id": 0, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": -1, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 2**63, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": "string_id", "method": "tools/list", "params": {}},
        ]
        crashes = 0
        for msg in cases:
            try:
                await self.client.send_raw(msg)
            except (ConnectionError, OSError):
                crashes += 1
                self._crash_count += 1
            except Exception:
                pass
        duration = (time.monotonic() - start) * 1000
        if crashes > 0:
            return TestResult(
                name="boundary_values",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message=f"{crashes} crashes from boundary values",
            )
        return TestResult(
            name="boundary_values",
            status=TestStatus.PASS,
            duration_ms=duration,
            message="Server handled boundary values gracefully",
        )

    async def _test_null_bytes(self) -> TestResult:
        """Test handling of null bytes in strings."""
        start = time.monotonic()
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "echo" + "\x00" + "hidden", "arguments": {}},
        }
        try:
            await self.client.send_raw(msg)
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="null_bytes",
                status=TestStatus.PASS,
                duration_ms=duration,
                message="Server handled null bytes safely",
            )
        except (ConnectionError, OSError):
            duration = (time.monotonic() - start) * 1000
            self._crash_count += 1
            return TestResult(
                name="null_bytes",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Server crashed on null bytes",
            )
        except Exception:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="null_bytes",
                status=TestStatus.PASS,
                duration_ms=duration,
                message="Server rejected null bytes",
            )

    async def _test_encoding_issues(self) -> TestResult:
        """Test encoding edge cases."""
        start = time.monotonic()
        cases = [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "\x00", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "\x80\x81\x82", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "\r\n\r\n", "arguments": {}}},
        ]
        crashes = 0
        for msg in cases:
            try:
                await self.client.send_raw(msg)
            except (ConnectionError, OSError):
                crashes += 1
                self._crash_count += 1
            except Exception:
                pass
        duration = (time.monotonic() - start) * 1000
        if crashes > 0:
            return TestResult(
                name="encoding_issues",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message=f"{crashes} crashes from encoding issues",
            )
        return TestResult(
            name="encoding_issues",
            status=TestStatus.PASS,
            duration_ms=duration,
            message="Server handled encoding edge cases",
        )
