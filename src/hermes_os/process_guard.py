"""watchdog.py — Process watchdog for 24/7 runtime.

The ``Watchdog`` monitors a set of managed processes (each identified by a
string name).  When a process exits unexpectedly, the watchdog restarts it
(up to a configurable retry limit) and records restart history.  After
exceeding the retry limit within a window, the process is marked
``FAILED`` and no longer restarted (escalation).

Usage::

    wd = Watchdog()
    handle = wd.register("worker", target=worker_fn, restart=True)
    await wd.start()   # begins monitoring loop
    await wd.stop()    # stops monitoring
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class ProcessStatus(str, Enum):
    """Status of a managed process."""

    PENDING = "pending"
    RUNNING = "running"
    RESTARTING = "restarting"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class RestartRecord:
    """A single restart event."""

    timestamp: float
    exit_code: Optional[int] = None
    reason: str = ""


@dataclass
class ProcessHandle:
    """Handle to a managed process."""

    name: str
    status: ProcessStatus = ProcessStatus.PENDING
    pid: Optional[int] = None
    started_at: Optional[float] = None
    exited_at: Optional[float] = None
    exit_code: Optional[int] = None
    restart_count: int = 0
    restart_history: List[RestartRecord] = field(default_factory=list)
    task: Optional[asyncio.Task] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def uptime_seconds(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.exited_at or time.time()
        return max(0.0, end - self.started_at)


@dataclass
class WatchdogConfig:
    """Configuration for the watchdog.

    Parameters
    ----------
    check_interval
        How often (seconds) to poll managed processes.
    max_restarts
        Maximum restart attempts within ``restart_window_seconds``.
    restart_window_seconds
        Sliding window for counting restarts.
    restart_delay
        Delay (seconds) before restarting a failed process.
    backoff_factor
        Multiplicative factor for exponential backoff on restarts.
    max_restart_delay
        Cap on the restart delay.
    """

    check_interval: float = 1.0
    max_restarts: int = 5
    restart_window_seconds: float = 60.0
    restart_delay: float = 1.0
    backoff_factor: float = 2.0
    max_restart_delay: float = 60.0


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------


class Watchdog:
    """Process watchdog that monitors and restarts managed processes.

    Parameters
    ----------
    config
        Watchdog configuration.
    on_restart
        Optional callback ``(handle, record)`` invoked after each restart.
    on_failure
        Optional callback ``(handle)`` invoked when a process exceeds
        its restart budget and is marked ``FAILED``.
    """

    def __init__(
        self,
        config: Optional[WatchdogConfig] = None,
        on_restart: Optional[Callable[[ProcessHandle, RestartRecord], None]] = None,
        on_failure: Optional[Callable[[ProcessHandle], None]] = None,
    ) -> None:
        self._config = config or WatchdogConfig()
        self._on_restart = on_restart
        self._on_failure = on_failure
        self._processes: Dict[str, ProcessHandle] = {}
        self._targets: Dict[str, Callable[[], Awaitable[Any]]] = {}
        self._restart_flags: Dict[str, bool] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    # -- registration -------------------------------------------------------

    def register(
        self,
        name: str,
        target: Callable[[], Awaitable[Any]],
        restart: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessHandle:
        """Register a process to be managed.

        Parameters
        ----------
        name
            Unique name for the process.
        target
            Async callable that runs the process.  Should block until the
            process is done (e.g. ``await asyncio.sleep`` forever for a
            long-running service).
        restart
            If True, the watchdog will restart the process on failure.
        metadata
            Arbitrary metadata attached to the handle.
        """
        if name in self._processes:
            raise ValueError(f"process {name!r} already registered")
        handle = ProcessHandle(name=name, metadata=metadata or {})
        self._processes[name] = handle
        self._targets[name] = target
        self._restart_flags[name] = restart
        return handle

    def unregister(self, name: str) -> Optional[ProcessHandle]:
        """Unregister a process.  Returns the handle if found."""
        handle = self._processes.pop(name, None)
        self._targets.pop(name, None)
        self._restart_flags.pop(name, None)
        if handle and handle.task:
            handle.task.cancel()
        return handle

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the watchdog and all registered processes."""
        if self._running:
            return
        self._running = True
        for name in list(self._processes):
            await self._start_process(name)
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        log.info("watchdog started with %d processes", len(self._processes))

    async def stop(self) -> None:
        """Stop the watchdog and all managed processes."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        for name in list(self._processes):
            await self._stop_process(name)
        log.info("watchdog stopped")

    # -- queries ------------------------------------------------------------

    @property
    def processes(self) -> Dict[str, ProcessHandle]:
        return dict(self._processes)

    @property
    def running(self) -> bool:
        return self._running

    def get(self, name: str) -> Optional[ProcessHandle]:
        return self._processes.get(name)

    def status(self) -> Dict[str, Any]:
        """Return a summary of all managed processes."""
        return {
            "running": self._running,
            "total": len(self._processes),
            "processes": {
                name: {
                    "status": h.status.value,
                    "pid": h.pid,
                    "uptime_seconds": h.uptime_seconds,
                    "restart_count": h.restart_count,
                }
                for name, h in self._processes.items()
            },
        }

    # -- internal -----------------------------------------------------------

    async def _start_process(self, name: str) -> None:
        handle = self._processes.get(name)
        target = self._targets.get(name)
        if handle is None or target is None:
            return
        handle.status = ProcessStatus.RUNNING
        handle.started_at = time.time()
        handle.exited_at = None
        handle.exit_code = None
        handle.task = asyncio.create_task(self._run_process(name))

    async def _stop_process(self, name: str) -> None:
        handle = self._processes.get(name)
        if handle is None:
            return
        if handle.task and not handle.task.done():
            handle.task.cancel()
            try:
                await handle.task
            except asyncio.CancelledError:
                pass
        handle.status = ProcessStatus.STOPPED
        handle.exited_at = time.time()

    async def _run_process(self, name: str) -> None:
        """Run a single process and handle its completion."""
        target = self._targets[name]
        try:
            log.debug("process %s starting", name)
            await target()
            exit_code = 0
        except asyncio.CancelledError:
            exit_code = -1
            raise
        except Exception:
            log.exception("process %s crashed", name)
            exit_code = 1
        finally:
            await self._on_process_exit(name, exit_code)

    async def _on_process_exit(self, name: str, exit_code: int) -> None:
        handle = self._processes.get(name)
        if handle is None:
            return
        handle.exited_at = time.time()
        handle.exit_code = exit_code

        if not self._running:
            handle.status = ProcessStatus.STOPPED
            return

        should_restart = self._restart_flags.get(name, False)
        if not should_restart:
            handle.status = ProcessStatus.STOPPED
            return

        # Check restart budget
        now = time.time()
        window = self._config.restart_window_seconds
        recent = [r for r in handle.restart_history if now - r.timestamp < window]
        if len(recent) >= self._config.max_restarts:
            handle.status = ProcessStatus.FAILED
            log.error(
                "process %s exceeded restart budget (%d in %.0fs)",
                name,
                len(recent),
                window,
            )
            if self._on_failure:
                try:
                    self._on_failure(handle)
                except Exception:
                    log.exception("on_failure callback error")
            return

        # Compute backoff delay
        delay = min(
            self._config.restart_delay * (self._config.backoff_factor ** len(recent)),
            self._config.max_restart_delay,
        )
        handle.status = ProcessStatus.RESTARTING
        record = RestartRecord(
            timestamp=now,
            exit_code=exit_code,
            reason=f"exit_code={exit_code}",
        )
        handle.restart_history.append(record)
        handle.restart_count += 1

        if self._on_restart:
            try:
                self._on_restart(handle, record)
            except Exception:
                log.exception("on_restart callback error")

        log.info(
            "restarting process %s in %.1fs (attempt %d)",
            name,
            delay,
            handle.restart_count,
        )
        await asyncio.sleep(delay)
        if self._running:
            await self._start_process(name)

    async def _monitor_loop(self) -> None:
        """Periodically check process health."""
        while self._running:
            await asyncio.sleep(self._config.check_interval)
            for name, handle in list(self._processes.items()):
                if handle.status == ProcessStatus.RUNNING and handle.task:
                    if handle.task.done():
                        # Task finished without triggering _on_process_exit
                        try:
                            exc = handle.task.exception()
                            if exc and not isinstance(exc, asyncio.CancelledError):
                                log.error("process %s raised: %s", name, exc)
                                await self._on_process_exit(name, 1)
                        except asyncio.CancelledError:
                            pass
