"""
Compatibility facade: Capacity benchmarks have been relocated to the root 'benchmarks/' folder.

This module proxies submodule lookups and exports to 'benchmarks/' so existing imports
like `from src.benchmark.mmlu_benchmark import ...` continue to resolve seamlessly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_BENCHMARKS_DIR = str(_ROOT / "benchmarks")

if _BENCHMARKS_DIR not in sys.path:
    sys.path.insert(0, _BENCHMARKS_DIR)

__path__ = [_BENCHMARKS_DIR]

try:
    import benchmarks
    for _k, _v in benchmarks.__dict__.items():
        if not _k.startswith("_"):
            globals()[_k] = _v
except Exception:
    pass
