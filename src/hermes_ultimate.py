"""Backward-compatibility shim: hermes_ultimate is located in src.engines.hermes_ultimate."""
from .engines.hermes_ultimate import *

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
