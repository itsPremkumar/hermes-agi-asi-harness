"""Pytest configuration and fixtures."""

import pytest
import sys
import os

src_path = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.abspath(src_path))
