"""Backward-compatibility shim: hermes_supervisor is located in src.engines.hermes_supervisor."""
from .engines.hermes_supervisor import *

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
