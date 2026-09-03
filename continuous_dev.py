"""Forwarding shim: continuous_dev source is in src/continuous_dev.py."""
import sys
from pathlib import Path
_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.continuous_dev import *
