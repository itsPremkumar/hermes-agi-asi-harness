"""Conformance test suite for MCP protocol compliance."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from mcptest.config import Config
from mcptest.models import (
    ConformanceResult,
    TestResult,
    TestStatus,
    TestSuite,
)
from mcptest.client import MockMCPClient


class ConformanceTester:
    """Tests MCP server protocol compliance.

    Validates that a target MCP server correctly implements the
    Model Context Protocol specification: initialization, tool
    listing, tool invocation, resource access, and prompt handling.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = MockMCPClient(config)

    async def run(self) -> ConformanceResult:
        """Execute the full conformance test suite."""
        suite = TestSuite(name="MCP Conformance")

        tests = [
            self._test_init,
            self._test_initialize_response_schema,
            self._test_tools_list,
            self._test_tools_call,
            self._test_resources_list,
            self._test_resources_read,
            self._test_prompts_list,
            self._test_prompts_get,
            self._test_ping,
            self._test_error_invalid_jsonrpc,
            self._test_error_unknown_method,
            self._test_error_missing_params,
            self._test_tool_input_validation,
            self._test_content_types,
            self._test_idempotency,
        ]

        for test_fn in tests:
            result = await test_fn()
            suite.results.append(result)

        suite.finished_at = __import__("datetime").datetime.utcnow()

        return ConformanceResult(
            suite=suite,
            mcp_version="2024-11-05",
            server_name=self.config.target.name,
            transport=self.config.target.transport,
        )

    async def _test_init(self) -> TestResult:
        """Test server initialization handshake."""
        start = time.monotonic()
        try:
            resp = await self.client.initialize()
            duration = (time.monotonic() - start) * 1000
            if resp and "result" in resp:
                return TestResult(
                    name="init",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Server initialized successfully",
                )
            return TestResult(
                name="init",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Server returned unexpected init response",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="init",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=f"Init failed: {e}",
            )

    async def _test_initialize_response_schema(self) -> TestResult:
        """Test that initialize response follows MCP schema."""
        start = time.monotonic()
        try:
            resp = await self.client.initialize()
            duration = (time.monotonic() - start) * 1000
            result = resp.get("result", {})
            required = ["protocolVersion", "capabilities", "serverInfo"]
            missing = [k for k in required if k not in result]
            if missing:
                return TestResult(
                    name="init_response_schema",
                    status=TestStatus.FAIL,
                    duration_ms=duration,
                    message=f"Missing fields: {missing}",
                )
            return TestResult(
                name="init_response_schema",
                status=TestStatus.PASS,
                duration_ms=duration,
                message="Response schema valid",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="init_response_schema",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_tools_list(self) -> TestResult:
        """Test tools/list endpoint."""
        start = time.monotonic()
        try:
            resp = await self.client.list_tools()
            duration = (time.monotonic() - start) * 1000
            if "result" in resp and "tools" in resp["result"]:
                tools = resp["result"]["tools"]
                return TestResult(
                    name="tools_list",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message=f"Listed {len(tools)} tools",
                    details={"tool_count": len(tools)},
                )
            return TestResult(
                name="tools_list",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="tools/list response missing 'tools' field",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="tools_list",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_tools_call(self) -> TestResult:
        """Test tools/call endpoint."""
        start = time.monotonic()
        try:
            tools_resp = await self.client.list_tools()
            tools = tools_resp.get("result", {}).get("tools", [])
            if not tools:
                return TestResult(
                    name="tools_call",
                    status=TestStatus.SKIP,
                    duration_ms=(time.monotonic() - start) * 1000,
                    message="No tools available to call",
                )
            first_tool = tools[0]
            resp = await self.client.call_tool(first_tool["name"], {})
            duration = (time.monotonic() - start) * 1000
            if "result" in resp:
                return TestResult(
                    name="tools_call",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message=f"Called tool '{first_tool['name']}' successfully",
                )
            if "error" in resp:
                return TestResult(
                    name="tools_call",
                    status=TestStatus.FAIL,
                    duration_ms=duration,
                    message=f"Tool call error: {resp['error']}",
                )
            return TestResult(
                name="tools_call",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Unexpected response format",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="tools_call",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_resources_list(self) -> TestResult:
        """Test resources/list endpoint."""
        start = time.monotonic()
        try:
            resp = await self.client.list_resources()
            duration = (time.monotonic() - start) * 1000
            if "result" in resp:
                return TestResult(
                    name="resources_list",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Resources listed successfully",
                )
            if "error" in resp:
                code = resp["error"].get("code", 0)
                if code == -32601:
                    return TestResult(
                        name="resources_list",
                        status=TestStatus.SKIP,
                        duration_ms=duration,
                        message="Server does not support resources",
                    )
            return TestResult(
                name="resources_list",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Unexpected response",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="resources_list",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_resources_read(self) -> TestResult:
        """Test resources/read endpoint."""
        start = time.monotonic()
        try:
            resources_resp = await self.client.list_resources()
            resources = resources_resp.get("result", {}).get("resources", [])
            if not resources:
                return TestResult(
                    name="resources_read",
                    status=TestStatus.SKIP,
                    duration_ms=(time.monotonic() - start) * 1000,
                    message="No resources available",
                )
            resp = await self.client.read_resource(resources[0]["uri"])
            duration = (time.monotonic() - start) * 1000
            if "result" in resp:
                return TestResult(
                    name="resources_read",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Resource read successfully",
                )
            return TestResult(
                name="resources_read",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Resource read failed",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="resources_read",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_prompts_list(self) -> TestResult:
        """Test prompts/list endpoint."""
        start = time.monotonic()
        try:
            resp = await self.client.list_prompts()
            duration = (time.monotonic() - start) * 1000
            if "result" in resp:
                return TestResult(
                    name="prompts_list",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Prompts listed successfully",
                )
            if "error" in resp:
                code = resp["error"].get("code", 0)
                if code == -32601:
                    return TestResult(
                        name="prompts_list",
                        status=TestStatus.SKIP,
                        duration_ms=duration,
                        message="Server does not support prompts",
                    )
            return TestResult(
                name="prompts_list",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Unexpected response",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="prompts_list",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_prompts_get(self) -> TestResult:
        """Test prompts/get endpoint."""
        start = time.monotonic()
        try:
            prompts_resp = await self.client.list_prompts()
            prompts = prompts_resp.get("result", {}).get("prompts", [])
            if not prompts:
                return TestResult(
                    name="prompts_get",
                    status=TestStatus.SKIP,
                    duration_ms=(time.monotonic() - start) * 1000,
                    message="No prompts available",
                )
            resp = await self.client.get_prompt(prompts[0]["name"], {})
            duration = (time.monotonic() - start) * 1000
            if "result" in resp:
                return TestResult(
                    name="prompts_get",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Prompt retrieved successfully",
                )
            return TestResult(
                name="prompts_get",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Prompt get failed",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="prompts_get",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_ping(self) -> TestResult:
        """Test ping endpoint."""
        start = time.monotonic()
        try:
            resp = await self.client.ping()
            duration = (time.monotonic() - start) * 1000
            if "result" in resp:
                return TestResult(
                    name="ping",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Ping successful",
                )
            return TestResult(
                name="ping",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Ping failed",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="ping",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_error_invalid_jsonrpc(self) -> TestResult:
        """Test error handling for invalid JSON-RPC."""
        start = time.monotonic()
        try:
            resp = await self.client.send_raw({"jsonrpc": "2.0", "id": 1, "method": "nonexistent"})
            duration = (time.monotonic() - start) * 1000
            if "error" in resp:
                return TestResult(
                    name="error_invalid_jsonrpc",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Server returned proper error for unknown method",
                )
            return TestResult(
                name="error_invalid_jsonrpc",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Server did not return error for unknown method",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="error_invalid_jsonrpc",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_error_unknown_method(self) -> TestResult:
        """Test error for unknown method."""
        start = time.monotonic()
        try:
            resp = await self.client.send_raw({"jsonrpc": "2.0", "id": 2, "method": "foobar"})
            duration = (time.monotonic() - start) * 1000
            if "error" in resp and resp["error"].get("code") == -32601:
                return TestResult(
                    name="error_unknown_method",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Correct -32601 error code returned",
                )
            return TestResult(
                name="error_unknown_method",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Expected -32601 Method not found",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="error_unknown_method",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_error_missing_params(self) -> TestResult:
        """Test error for missing required parameters."""
        start = time.monotonic()
        try:
            resp = await self.client.send_raw({"jsonrpc": "2.0", "id": 3, "method": "tools/call"})
            duration = (time.monotonic() - start) * 1000
            if "error" in resp:
                return TestResult(
                    name="error_missing_params",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Server returned error for missing params",
                )
            return TestResult(
                name="error_missing_params",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="Server accepted call without required params",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="error_missing_params",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_tool_input_validation(self) -> TestResult:
        """Test that tools validate input against their schemas."""
        start = time.monotonic()
        try:
            tools_resp = await self.client.list_tools()
            tools = tools_resp.get("result", {}).get("tools", [])
            if not tools:
                return TestResult(
                    name="tool_input_validation",
                    status=TestStatus.SKIP,
                    duration_ms=(time.monotonic() - start) * 1000,
                    message="No tools to test",
                )
            # Call with wrong type for a required param
            tool = tools[0]
            params = tool.get("inputSchema", {}).get("properties", {})
            if not params:
                return TestResult(
                    name="tool_input_validation",
                    status=TestStatus.SKIP,
                    duration_ms=(time.monotonic() - start) * 1000,
                    message="Tool has no input schema params",
                )
            bad_args = {k: 12345 for k in params}
            resp = await self.client.call_tool(tool["name"], bad_args)
            duration = (time.monotonic() - start) * 1000
            if "error" in resp:
                return TestResult(
                    name="tool_input_validation",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="Server rejected invalid input",
                )
            return TestResult(
                    name="tool_input_validation",
                    status=TestStatus.FAIL,
                    duration_ms=duration,
                    message="Server accepted invalid input",
                )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="tool_input_validation",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_content_types(self) -> TestResult:
        """Test that content types are valid per MCP spec."""
        start = time.monotonic()
        try:
            tools_resp = await self.client.list_tools()
            tools = tools_resp.get("result", {}).get("tools", [])
            if not tools:
                return TestResult(
                    name="content_types",
                    status=TestStatus.SKIP,
                    duration_ms=(time.monotonic() - start) * 1000,
                    message="No tools to test",
                )
            resp = await self.client.call_tool(tools[0]["name"], {})
            duration = (time.monotonic() - start) * 1000
            result = resp.get("result", {})
            content = result.get("content", [])
            valid_types = {"text", "image", "resource"}
            for item in content:
                if item.get("type") not in valid_types:
                    return TestResult(
                        name="content_types",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        message=f"Invalid content type: {item.get('type')}",
                    )
            return TestResult(
                name="content_types",
                status=TestStatus.PASS,
                duration_ms=duration,
                message="All content types valid",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="content_types",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )

    async def _test_idempotency(self) -> TestResult:
        """Test that read operations are idempotent."""
        start = time.monotonic()
        try:
            resp1 = await self.client.list_tools()
            resp2 = await self.client.list_tools()
            duration = (time.monotonic() - start) * 1000
            if resp1 == resp2:
                return TestResult(
                    name="idempotency",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message="tools/list is idempotent",
                )
            return TestResult(
                name="idempotency",
                status=TestStatus.FAIL,
                duration_ms=duration,
                message="tools/list returned different results",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return TestResult(
                name="idempotency",
                status=TestStatus.ERROR,
                duration_ms=duration,
                message=str(e),
            )
