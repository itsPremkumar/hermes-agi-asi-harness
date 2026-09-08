"""
pytest configuration — ensure the local src/ directory is on sys.path.
"""

import sys
from pathlib import Path

# Put the local src/ directory at the front of sys.path so our harness package
# takes precedence over any other workspace's harness package.
_src_dir = str(Path(__file__).parent.parent / "src")
if _src_dir in sys.path:
    sys.path.remove(_src_dir)
sys.path.insert(0, _src_dir)
