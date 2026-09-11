"""Pytest configuration and fixtures for DeepResearch tests."""

import os
import sys
import tempfile
import pytest

# Ensure the workspace root is on sys.path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Set offline mode for tests (no API key needed)
os.environ.setdefault("DR_LLM_PROVIDER", "nous")
os.environ.setdefault("DR_API_KEY", "")


@pytest.fixture(autouse=True)
def clean_llm_cache():
    """Clear LLM cache before each test for deterministic results."""
    from deepresearch.providers.llm import clear_cache
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def temp_db():
    """Provide a temporary database path for memory tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)
