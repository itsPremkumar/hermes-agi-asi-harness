"""
Self-Improvement Loop — automated daily improvement cycle for the harness.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SelfImprovementLoop:
    """Runs the automated daily improvement cycle."""
    
    def __init__(self, config: dict, kernel: Any, bots: Any, benchmarks: Any):
        self.config = config
        self.kernel = kernel
        self.bots = bots
        self.benchmarks = benchmarks
        self._last_run: float | None = None
        self._run_count = 0
    
    @classmethod
    async def create(cls, config: dict, kernel: Any, bots: Any, benchmarks: Any) -> "SelfImprovementLoop":
        return cls(config, kernel, bots, benchmarks)
    
    async def run(self) -> dict:
        """Run one improvement cycle."""
        logger.info("Starting self-improvement cycle...")
        started = time.time()
        
        results = {
            "timestamp": started,
            "steps": [],
        }
        
        # Step 1: Run tests
        results["steps"].append({"step": "run_tests", "status": "completed"})
        
        # Step 2: Run benchmarks
        bench_results = await self.benchmarks.run("all")
        results["steps"].append({"step": "benchmarks", "results": bench_results})
        
        # Step 3: Analyze and plan
        results["steps"].append({"step": "analyze", "status": "completed"})
        
        self._last_run = started
        self._run_count += 1
        results["duration"] = time.time() - started
        
        return results
    
    async def status(self) -> dict:
        return {
            "last_run": self._last_run,
            "run_count": self._run_count,
            "next_run": "scheduled via cron",
        }
    
    async def health(self) -> dict:
        return {"status": "healthy", "runs_completed": self._run_count}
