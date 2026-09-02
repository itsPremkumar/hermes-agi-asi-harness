"""Tests for contract testing."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from testpilot.contract_testing import (
    ContractVerifier,
    create_pact,
    load_pact_file,
    save_pact,
)
from testpilot.models import ContractDefinition


def test_create_pact() -> None:
    """Should create a contract definition."""
    contract = create_pact(
        consumer="web",
        provider="api",
        interactions=[
            {"description": "get user", "request": {"method": "GET", "path": "/users/1"}}
        ],
    )
    assert contract.consumer == "web"
    assert len(contract.interactions) == 1


def test_save_and_load_pact(tmp_path: Path) -> None:
    """Should save and load pact files."""
    contract = create_pact("test-consumer", "test-provider", interactions=[])

    path = tmp_path / "test-pact.json"
    save_pact(contract, path)

    assert path.exists()
    loaded = load_pact_file(path)
    assert loaded.consumer == "test-consumer"
    assert loaded.provider == "test-provider"


def test_verify_interaction_success() -> None:
    """Should pass when response matches contract."""
    verifier = ContractVerifier("http://localhost:8080")

    contract = ContractDefinition(
        consumer="web",
        provider="api",
        interactions=[
            {
                "description": "get health",
                "request": {"method": "GET", "path": "/health"},
                "response": {"status": 200},
            }
        ],
    )

    # Mock the httpx.request call
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"{}"
    mock_response.json.return_value = {}

    with patch("httpx.request", return_value=mock_response):
        result = verifier.verify_contract(contract)

    assert result.passed is True
    assert result.interactions[0].passed is True


def test_verify_interaction_failure() -> None:
    """Should fail when response does not match contract."""
    verifier = ContractVerifier("http://localhost:8080")

    contract = ContractDefinition(
        consumer="web",
        provider="api",
        interactions=[
            {
                "description": "get users",
                "request": {"method": "GET", "path": "/users"},
                "response": {"status": 200},
            }
        ],
    )

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.content = b"error"

    with patch("httpx.request", return_value=mock_response):
        result = verifier.verify_contract(contract)

    assert result.passed is False
    assert "500" in result.interactions[0].error_message
