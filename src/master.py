"""Backward-compatibility shim: master is located in src.engines.master."""
from .engines.master import *

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
