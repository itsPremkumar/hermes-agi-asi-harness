"""Pytest configuration and fixtures."""
import os
import sys
from pathlib import Path

# Ensure workspace root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure asyncio mode for pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# Ensure temporary memory dirs don't interfere with real ones
os.environ.setdefault("DEEPRESEARCH_TEST_MODE", "1")
