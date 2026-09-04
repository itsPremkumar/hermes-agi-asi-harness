"""
Boot script — loads the bridge when Hermes starts.

Add to Hermes config.yaml:
    hooks:
      on_session_start: python -m integration.hermes_bridge.boot
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def boot():
    """Boot the Hermes Bridge."""
    try:
        from integration.hermes_bridge import HermesBridge
        
        bridge = await HermesBridge.create()
        
        # Store in global state for access from Hermes
        import builtins
        builtins.__harnix_bridge__ = bridge
        
        logger.info("Hermes Bridge initialized successfully")
        logger.info(f"Kernel state: {await bridge.kernel.status()}")
        logger.info(f"Available bots: {len(bridge.bots.profiles)}")
        
        return bridge
        
    except Exception as e:
        logger.error(f"Failed to boot Hermes Bridge: {e}")
        raise


if __name__ == "__main__":
    bridge = asyncio.run(boot())
    print("Hermes Bridge ready. Access via __harnix_bridge__")
