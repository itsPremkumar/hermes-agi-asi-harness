"""Backward-compatibility facade: agent is unified into src.agents."""
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.agents import *
try:
    from src.agents.executive_agent import *
except ImportError:
    pass
