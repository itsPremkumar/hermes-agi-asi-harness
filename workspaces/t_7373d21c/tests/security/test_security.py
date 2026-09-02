"""Tests for MCPTest security scanner."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from mcptest.config import Config, ServerTarget
from mcptest.security import SecurityScanner
from mcptest.models import TestStatus, Severity


@pytest.fixture
def config():
    return Config(
        target=ServerTarget(name="test-server", transport="stdio"),
    )


@pytest.fixture
def scanner(config):
    return SecurityScanner(config)


class TestSecurityScanner:
    """Tests for the security scanner."""

    @pytest.mark.asyncio
    async def test_injection_no_vulns(self, scanner):
        with patch.object(
            scanner.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602}},
        ):
            result = await scanner._test_injection()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_auth_https(self, scanner):
        scanner.config.target.url = "https://example.com"
        result = await scanner._test_auth()
        assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_auth_http_warning(self, scanner):
        scanner.config.target.url = "http://example.com"
        result = await scanner._test_auth()
        assert result.status == TestStatus.FAIL
        assert len(scanner.findings) > 0

    @pytest.mark.asyncio
    async def test_cryptography_https(self, scanner):
        scanner.config.target.url = "https://example.com"
        result = await scanner._test_cryptography()
        assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_ssrf_no_vulns(self, scanner):
        with patch.object(
            scanner.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602}},
        ):
            result = await scanner._test_ssrf()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_info_disclosure_clean(self, scanner):
        with patch.object(
            scanner.client,
            "send_raw",
            return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}},
        ):
            result = await scanner._test_info_disclosure()
            assert result.status == TestStatus.PASS

    @pytest.mark.asyncio
    async def test_cors_skip_for_stdio(self, scanner):
        scanner.config.target.transport = "stdio"
        scanner.config.target.url = ""
        result = await scanner._test_cors()
        assert result.status == TestStatus.SKIP

    @pytest.mark.asyncio
    async def test_rate_limiting(self, scanner):
        with patch.object(
            scanner.client,
            "list_tools",
            return_value={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
        ):
            result = await scanner._test_rate_limiting()
            assert result.status == TestStatus.PASS
