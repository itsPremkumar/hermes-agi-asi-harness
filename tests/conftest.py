"""Pytest configuration for tests."""
import sys
from pathlib import Path

# Add src/ to sys.path for all tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
