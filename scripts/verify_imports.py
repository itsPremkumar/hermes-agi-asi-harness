"""Verify that all key package imports work (CI step)."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on the path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

imports = [
    "core",
    "plugins",
    "hermes_agi",
    "core.avo",
    "core.continuous",
    "core.benchmark.harness",
]

failed = []
for mod in imports:
    try:
        __import__(mod)
    except Exception as e:
        failed.append(f"{mod}: {e}")
        print(f"FAIL {mod}")
    else:
        print(f"OK {mod}")

if failed:
    print(f"\n{len(failed)} import(s) failed")
    sys.exit(1)
print("\nAll imports OK")
