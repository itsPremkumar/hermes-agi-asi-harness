"""Forwarding shim: safety_plugin source is in src/engines/safety_plugin.py."""
import sys
from pathlib import Path
_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.engines.safety_plugin import *
