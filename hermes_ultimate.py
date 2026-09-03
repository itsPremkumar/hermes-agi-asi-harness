"""Forwarding shim: hermes_ultimate source is in src/hermes_ultimate.py."""
import sys
from pathlib import Path
_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.hermes_ultimate import *

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
