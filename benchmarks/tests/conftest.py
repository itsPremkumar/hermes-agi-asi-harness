"""Pytest configuration and fixtures for benchmarks."""

import os
import sys

benchmarks_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(benchmarks_dir, ".."))
sys.path.insert(0, benchmarks_dir)
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "src"))
