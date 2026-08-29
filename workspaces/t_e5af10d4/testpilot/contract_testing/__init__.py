"""API contract testing — Pact-compatible consumer-driven contracts."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import jsonschema

from testpilot.models import ContractDefinition, GateStatus, QualityGateResult


@dataclass
class InteractionResult:
    """Result of verifying a single contract interaction."""
    description: str
    passed: bool
    request: dict[str, Any] = field(default_factory=dict)
    expected_response: dict[str, Any] = field(default_factory=dict)
    actual_response: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


@dataclass
class ContractResult:
    """Result of verifying an entire contract."""
    consumer: str
    provider: str
    passed: bool
    interactions: list[InteractionResult] = field(default_factory=list)


class ContractVerifier:
    """Verifies API contracts (Pact-compatible format)."""

    def __init__(self, provider_base_url: str, timeout: float = 10.0) -> None:
        self.provider_base_url = provider_base_url.rstrip("/")
        self.timeout = timeout

    def verify_contract(self, contract: ContractDefinition) -> ContractResult:
        """Verify all interactions in a contract."""
        results = []
        all_passed = True

        for interaction in contract.interactions:
            result = self._verify_interaction(interaction)
            results.append(result)
            if not result.passed:
                all_passed = False

        return ContractResult(
            consumer=contract.consumer,
            provider=contract.provider,
            passed=all_passed,
            interactions=results,
        )

    def _verify_interaction(self, interaction: dict[str, Any]) -> InteractionResult:
        """Verify a single interaction against the provider."""
        request = interaction.get("request", {})
        expected = interaction.get("response", {})

        method = request.get("method", "GET").upper()
        path = request.get("path", "/")
        headers = request.get("headers", {})
        body = request.get("body")

        url = f"{self.provider_base_url}{path}"

        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                json=body,
                timeout=self.timeout,
            )

            actual_status = response.status_code
            expected_status = expected.get("status", 200)

            if actual_status != expected_status:
                return InteractionResult(
                    description=interaction.get("description", ""),
                    passed=False,
                    request=request,
                    expected_response=expected,
                    actual_response={"status": actual_status, "body": response.text},
                    error_message=(
                        f"Status mismatch: expected {expected_status}, got {actual_status}"
                    ),
                )

            # Validate response body against schema if provided
            if "body" in expected and "schema" in expected:
                try:
                    actual_body = response.json()
                    jsonschema.validate(actual_body, expected["schema"])
                except jsonschema.ValidationError as e:
                    return InteractionResult(
                        description=interaction.get("description", ""),
                        passed=False,
                        request=request,
                        expected_response=expected,
                        actual_response={"status": actual_status, "body": response.json()},
                        error_message=f"Schema validation failed: {e.message}",
                    )

            return InteractionResult(
                description=interaction.get("description", ""),
                passed=True,
                request=request,
                expected_response=expected,
                actual_response={"status": actual_status, "body": response.json() if response.content else {}},
            )

        except httpx.TimeoutException:
            return InteractionResult(
                description=interaction.get("description", ""),
                passed=False,
                request=request,
                expected_response=expected,
                error_message=f"Request timed out after {self.timeout}s",
            )
        except Exception as e:
            return InteractionResult(
                description=interaction.get("description", ""),
                passed=False,
                request=request,
                expected_response=expected,
                error_message=str(e),
            )

    def verify_from_file(self, pact_path: str | Path) -> ContractResult:
        """Load and verify a contract from a JSON file."""
        contract = load_pact_file(pact_path)
        return self.verify_contract(contract)

    def verify_from_directory(self, pact_dir: str | Path) -> list[ContractResult]:
        """Load and verify all pact files in a directory."""
        results = []
        for pact_file in Path(pact_dir).glob("*.json"):
            result = self.verify_from_file(pact_file)
            results.append(result)
        return results

    def to_quality_gate(self, results: list[ContractResult]) -> QualityGateResult:
        """Convert contract results to a quality gate."""
        total = sum(len(r.interactions) for r in results)
        failed = sum(
            sum(1 for i in r.interactions if not i.passed) for r in results
        )
        passed = total - failed

        details: dict[str, Any] = {
            "total_contracts": len(results),
            "total_interactions": total,
            "passed": passed,
            "failed": failed,
            "failures": [
                {
                    "consumer": r.consumer,
                    "provider": r.provider,
                    "interaction": i.description,
                    "error": i.error_message,
                }
                for r in results
                for i in r.interactions
                if not i.passed
            ],
        }

        status = GateStatus.PASS if failed == 0 else GateStatus.FAIL
        return QualityGateResult(
            name="contract_testing",
            status=status,
            message=f"{passed}/{total} contract interactions passed",
            details=details,
        )


def load_pact_file(path: str | Path) -> ContractDefinition:
    """Load a Pact contract definition from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ContractDefinition(**data)


def create_pact(
    consumer: str,
    provider: str,
    interactions: list[dict[str, Any]],
) -> ContractDefinition:
    """Create a Pact contract definition."""
    return ContractDefinition(
        consumer=consumer,
        provider=provider,
        interactions=interactions,
    )


def save_pact(contract: ContractDefinition, path: str | Path) -> Path:
    """Save a Pact contract to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(contract.model_dump(), indent=2),
        encoding="utf-8",
    )
    return path
