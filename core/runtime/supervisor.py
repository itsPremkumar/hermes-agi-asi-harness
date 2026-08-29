"""
24/7 Supervisor Daemon — Continuous Operation & Health Monitoring

Ensures the system runs continuously, restarts on failure,
monitors health, and triggers daily development + verification cycles.
"""

import asyncio
import os
import sys
import time
import json
import signal
import subprocess
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.runtime.kernel import HermesKernel, KernelConfig
from core.verification import MultiRoundVerifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SupervisionConfig:
    """Configuration for the supervisor daemon."""
    project_root: str = str(Path(__file__).parent.parent.parent)
    health_check_interval: int = 30
    verification_interval_hours: int = 6
    daily_dev_interval_hours: int = 24
    restart_on_failure: bool = True
    max_restarts: int = 5
    restart_window_minutes: int = 60
    enable_daily_dev: bool = True
    enable_verification: bool = True
    enable_real_env_check: bool = True
    log_file: str = "supervisor.log"


@dataclass
class DaemonHealth:
    """Health status of the daemon and system."""
    running: bool = True
    kernel_healthy: bool = False
    last_heartbeat: float = 0.0
    last_verification: Optional[float] = None
    last_daily_dev: Optional[float] = None
    last_real_env_check: Optional[float] = None
    restart_count: int = 0
    failures: List[str] = field(default_factory=list)
    uptime_seconds: float = 0.0
    start_time: float = 0.0


class SupervisorDaemon:
    """24/7 Supervisor Daemon."""

    def __init__(self, config: SupervisionConfig = None):
        self.config = config or SupervisionConfig()
        self.health = DaemonHealth()
        self._kernel: Optional[HermesKernel] = None
        self._running = False
        self._restart_times: List[float] = []
        self._start_time = 0.0
        self._last_health_check = 0.0
        self._last_verification = 0.0
        self._last_daily_dev = 0.0
        self._last_real_env = 0.0

    def _make_kernel(self) -> HermesKernel:
        """Create a kernel with proper config."""
        config = KernelConfig(
            plugins_root=Path(self.config.project_root) / "plugins",
            hermes_home=Path(self.config.project_root) / ".hermes",
        )
        return HermesKernel(config)

    async def start(self):
        """Start the supervisor daemon."""
        self._running = True
        self._start_time = time.time()
        self.health.start_time = self._start_time
        
        logger.info("SupervisorDaemon starting...")
        logger.info(f"Project root: {self.config.project_root}")
        
        pid_file = Path(self.config.project_root) / ".supervisor.pid"
        pid_file.write_text(str(os.getpid()))
        
        try:
            await self._main_loop()
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        finally:
            await self._shutdown()
            pid_file.unlink(missing_ok=True)

    async def _main_loop(self):
        """Main supervision loop."""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Error in supervision tick: {e}")
                self.health.failures.append(f"{time.time()}: {e}")
            await asyncio.sleep(self.config.health_check_interval)

    async def _tick(self):
        """Single supervision tick."""
        now = time.time()
        self.health.uptime_seconds = now - self._start_time
        self.health.last_heartbeat = now
        
        await self._check_kernel_health()
        
        if self.config.enable_verification:
            if now - self._last_verification >= self.config.verification_interval_hours * 3600:
                logger.info("Running verification cycle...")
                await self._run_verification()
                self._last_verification = now
                self.health.last_verification = now
        
        if self.config.enable_daily_dev:
            if now - self._last_daily_dev >= self.config.daily_dev_interval_hours * 3600:
                logger.info("Running daily development cycle...")
                await self._run_daily_development()
                self._last_daily_dev = now
                self.health.last_daily_dev = now
        
        if self.config.enable_real_env_check:
            if now - self._last_real_env >= self.config.verification_interval_hours * 3600:
                logger.info("Running real-environment check...")
                await self._run_real_env_check()
                self._last_real_env = now
                self.health.last_real_env_check = now
        
        self._last_health_check = now

    async def _check_kernel_health(self):
        """Check that the kernel is alive and healthy."""
        try:
            if self._kernel is None:
                self._kernel = self._make_kernel()
                await self._kernel.boot()
            
            healthy = await self._kernel.health_check()
            self.health.kernel_healthy = healthy["status"] == "healthy"
            
            if not self.health.kernel_healthy:
                logger.warning("Kernel unhealthy, attempting restart...")
                await self._restart_kernel()
        except Exception as e:
            logger.error(f"Kernel health check failed: {e}")
            self.health.kernel_healthy = False
            if self.config.restart_on_failure:
                await self._restart_kernel()

    async def _restart_kernel(self):
        """Restart the kernel."""
        if self._kernel:
            await self._kernel.shutdown()
            self._kernel = None
        
        self._restart_times.append(time.time())
        cutoff = time.time() - self.config.restart_window_minutes * 60
        self._restart_times = [t for t in self._restart_times if t > cutoff]
        
        if len(self._restart_times) > self.config.max_restarts:
            logger.error("Max restarts exceeded, entering fail-safe mode")
            self._running = False
            return
        
        self.health.restart_count += 1
        logger.info(f"Restarting kernel (attempt {self.health.restart_count})")
        self._kernel = self._make_kernel()
        await self._kernel.boot()

    async def _run_verification(self):
        """Run multi-round verification."""
        verifier = MultiRoundVerifier(self.config.project_root)
        test_files = [str(f) for f in sorted(Path(self.config.project_root).glob("test_*.py"))]
        test_files = [f for f in test_files if "test_working" not in f]
        plan = verifier.create_plan(test_files, num_rounds=3)
        result = await verifier.run_verification(plan)
        if not result["overall_passed"]:
            logger.warning(f"Verification failed")
            self.health.failures.append(f"{time.time()}: Verification failed")

    async def _run_daily_development(self):
        """Run daily development cycle."""
        logger.info("Starting daily development cycle")
        try:
            from core.runtime.daily_dev import DailyDevEngine, DailyDevConfig
            config = DailyDevConfig(project_root=self.config.project_root)
            engine = DailyDevEngine(config)
            result = await engine.run_daily_cycle()
            logger.info(f"Daily dev cycle: {result['ideas_implemented']} implemented, verification={'PASSED' if result['verification_passed'] else 'FAILED'}")
        except Exception as e:
            logger.error(f"Daily dev failed: {e}")

    async def _run_real_env_check(self):
        """Run real-environment validation."""
        logger.info("Running real-environment validation")
        try:
            from core.runtime.daily_dev import DailyDevEngine, DailyDevConfig
            config = DailyDevConfig(project_root=self.config.project_root)
            engine = DailyDevEngine(config)
            result = await engine.run_real_env_check()
            logger.info(f"Real-env check: {'PASSED' if result['passed'] else 'FAILED'}")
        except Exception as e:
            logger.error(f"Real-env check failed: {e}")

    async def _shutdown(self):
        """Graceful shutdown."""
        logger.info("Supervisor shutting down...")
        self._running = False
        if self._kernel:
            await self._kernel.shutdown()
        logger.info("Supervisor stopped.")

    def get_health(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            "running": self.health.running,
            "kernel_healthy": self.health.kernel_healthy,
            "last_heartbeat": self.health.last_heartbeat,
            "uptime_seconds": self.health.uptime_seconds,
            "restart_count": self.health.restart_count,
            "last_verification": self.health.last_verification,
            "last_daily_dev": self.health.last_daily_dev,
            "last_real_env_check": self.health.last_real_env_check,
            "failures": self.health.failures[-10:],
        }


class SupervisorDaemonPlugin:
    """Plugin wrapper for the supervisor daemon."""

    def __init__(self):
        self._daemon: Optional[SupervisorDaemon] = None
        self._config = SupervisionConfig()

    async def load(self):
        self._daemon = SupervisorDaemon(self._config)

    async def start(self):
        if self._daemon:
            asyncio.create_task(self._daemon.start())

    async def stop(self):
        if self._daemon:
            await self._daemon._shutdown()

    async def health(self):
        if self._daemon:
            return self._daemon.get_health()
        return {"status": "not_started"}


async def create(kernel=None):
    plugin = SupervisorDaemonPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
