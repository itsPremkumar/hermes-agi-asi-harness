"""Backward-compatibility shim: hermes_engine is located in src.engines.hermes_engine."""
from .engines.hermes_engine import *

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
