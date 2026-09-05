"""Auto-add src and benchmarks to sys.path for hermes-agi-asi-harness."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = str(_ROOT / "src")
_BENCHMARKS = str(_ROOT / "benchmarks")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
if _BENCHMARKS not in sys.path:
    sys.path.insert(0, _BENCHMARKS)
