"""Backward-compatibility facade: tools source is now in src/tools."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = str(_ROOT / "src")
_SRC_PKG = str(_ROOT / "src" / "tools")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

__path__ = [_SRC_PKG]

try:
    from src.tools import *
except Exception:
    pass
