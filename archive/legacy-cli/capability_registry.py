"""Forwarding shim: capability_registry source is in src/engines/capability_registry.py."""
import sys
from pathlib import Path
_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.engines.capability_registry import *
