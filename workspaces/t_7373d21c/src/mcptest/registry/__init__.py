"""MCPHub registry integration for MCPTest."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from mcptest.config import Config
from mcptest.models import ComplianceReport


class RegistryError(Exception):
    """Raised when registry operations fail."""


class MCPHubRegistry:
    """Integrates with the MCPHub registry for compliance data.

    Publishes test results, retrieves server metadata, and
    manages compliance badge status.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.base_url = config.registry_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "MCPTest/1.0.0",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def publish_report(self, report: ComplianceReport) -> dict[str, Any]:
        """Publish a compliance report to the registry.

        Returns the registry response with report ID and status.
        """
        client = await self._get_client()

        payload = {
            "server_name": report.server_name,
            "server_version": report.server_version,
            "mcp_version": report.mcp_version,
            "overall_score": report.overall_score,
            "badge_eligible": report.badge_eligible,
            "conformance_pass_rate": None,
            "security_findings_count": 0,
            "benchmark_rps": 0.0,
            "generated_at": report.generated_at.isoformat(),
        }

        if report.conformance:
            total = report.conformance.suite.total
            if total > 0:
                payload["conformance_pass_rate"] = (
                    report.conformance.suite.passed / total
                )

        if report.security:
            payload["security_findings_count"] = len(report.security.findings)

        if report.benchmark:
            payload["benchmark_rps"] = report.benchmark.requests_per_second

        try:
            resp = await client.post("/reports", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise RegistryError(f"Failed to publish report: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RegistryError(f"Connection error: {e}") from e

    async def get_server_metadata(self, server_name: str) -> dict[str, Any]:
        """Retrieve server metadata from the registry."""
        client = await self._get_client()

        try:
            resp = await client.get(f"/servers/{server_name}")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise RegistryError(f"Failed to get metadata: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RegistryError(f"Connection error: {e}") from e

    async def get_compliance_status(self, server_name: str) -> dict[str, Any]:
        """Get the latest compliance status for a server."""
        client = await self._get_client()

        try:
            resp = await client.get(f"/servers/{server_name}/compliance")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "unknown"}
            raise RegistryError(f"Failed to get compliance: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RegistryError(f"Connection error: {e}") from e

    async def verify_badge(self, server_name: str) -> bool:
        """Verify if a server's compliance badge is valid."""
        status = await self.get_compliance_status(server_name)
        return status.get("badge_valid", False)

    def save_report_local(self, report: ComplianceReport) -> Path:
        """Save report locally as a fallback."""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        path = output_dir / f"report-{report.server_name}-{timestamp}.json"

        data = {
            "server_name": report.server_name,
            "server_version": report.server_version,
            "mcp_version": report.mcp_version,
            "overall_score": report.overall_score,
            "badge_eligible": report.badge_eligible,
            "generated_at": report.generated_at.isoformat(),
        }

        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path
