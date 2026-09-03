"""Forwarding shim: harness_control_plane source is in src/harness_control_plane.py."""
import sys
from pathlib import Path
_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.harness_control_plane import *
