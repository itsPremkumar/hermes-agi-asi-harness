"""
HERMES INTELLIGENCE OS — PLANE 18B: 24/7 BACKGROUND DAEMON & RESUMABLE CHECKPOINTS
===================================================================================
Prime Agent & DeerFlow inspired persistent daemon runtime:
- Event-driven wake and continuous background execution
- Resumable state persistence across crashes, disconnects, and process restarts
- Checkpoint / snapshot serialization to `.hermes/checkpoints/`
- Prioritized background mission queue
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger("hermes.os.daemon")


class MissionPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CheckpointSnapshot:
    """Complete checkpoint of an in-flight mission for disaster recovery."""

    checkpoint_id: str
    mission_id: str
    objective: str
    completed_steps: list[str]
    pending_steps: list[str]
    state_registers: dict[str, Any]
    world_state_summary: str
    tokens_consumed: int
    status: str  # in_progress, completed, failed, paused
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "mission_id": self.mission_id,
            "objective": self.objective,
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "state_registers": self.state_registers,
            "world_state_summary": self.world_state_summary,
            "tokens_consumed": self.tokens_consumed,
            "status": self.status,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointSnapshot:
        return cls(
            checkpoint_id=data["checkpoint_id"],
            mission_id=data["mission_id"],
            objective=data.get("objective", ""),
            completed_steps=data.get("completed_steps", []),
            pending_steps=data.get("pending_steps", []),
            state_registers=data.get("state_registers", {}),
            world_state_summary=data.get("world_state_summary", ""),
            tokens_consumed=data.get("tokens_consumed", 0),
            status=data.get("status", "in_progress"),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class QueuedMission:
    mission_id: str
    request: str
    priority: MissionPriority
    risk_level: str
    submitted_at: float = field(default_factory=time.time)


class PersistentDaemonRuntime:
    """
    24/7 background runtime managing checkpoints, crash recovery,
    and event-driven mission scheduling.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.hermes_dir = Path(workspace_root) / ".hermes"
        self.checkpoint_dir = self.hermes_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._queue_file = self.hermes_dir / "daemon_queue.json"
        self._pid_file = self.hermes_dir / "daemon.pid"
        self._stop_file = self.hermes_dir / "daemon.stop"
        self._queue: list[QueuedMission] = []
        self._checkpoints: dict[str, CheckpointSnapshot] = {}
        self._is_running: bool = False
        self._stop_requested: bool = False
        self._iterations_completed: int = 0
        self._consecutive_failures: int = 0
        self._load_existing_checkpoints()
        self._load_queue()

    def _load_existing_checkpoints(self):
        for f in self.checkpoint_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                snap = CheckpointSnapshot.from_dict(data)
                self._checkpoints[snap.mission_id] = snap
            except Exception as e:
                logger.debug("Failed loading checkpoint %s: %s", f, e)

    def save_checkpoint(self, snapshot: CheckpointSnapshot) -> str:
        """Persist mission state to disk."""
        self._checkpoints[snapshot.mission_id] = snapshot
        target = self.checkpoint_dir / f"{snapshot.mission_id}.json"
        target.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
        return snapshot.checkpoint_id

    def load_checkpoint(self, mission_id: str) -> Optional[CheckpointSnapshot]:
        return self._checkpoints.get(mission_id)

    def enqueue_mission(
        self,
        request: str,
        priority: MissionPriority = MissionPriority.NORMAL,
        risk_level: str = "medium",
    ) -> str:
        """Submit a task to the background queue (disk-persisted)."""
        mid = f"m-{uuid.uuid4().hex[:6]}"
        item = QueuedMission(
            mission_id=mid,
            request=request,
            priority=priority,
            risk_level=risk_level,
        )
        self._queue.append(item)
        # Sort queue by priority: CRITICAL > HIGH > NORMAL > LOW
        p_weights = {
            MissionPriority.CRITICAL: 4,
            MissionPriority.HIGH: 3,
            MissionPriority.NORMAL: 2,
            MissionPriority.LOW: 1,
        }
        self._queue.sort(key=lambda x: p_weights.get(x.priority, 0), reverse=True)
        self._save_queue()
        return mid

    def pop_next_mission(self) -> Optional[QueuedMission]:
        if not self._queue:
            return None
        item = self._queue.pop(0)
        self._save_queue()
        return item

    def pending_count(self) -> int:
        return len(self._queue)

    def active_checkpoints_count(self) -> int:
        return len(self._checkpoints)

    def reconstruct_from_crash(self) -> list[CheckpointSnapshot]:
        """Identify interrupted missions that were in progress during unexpected shutdown."""
        return [c for c in self._checkpoints.values() if c.status == "in_progress"]

    # ------------------------------------------------------------------
    # Continuous 24/7 runtime: disk-backed queue, pid lock, run loop
    # ------------------------------------------------------------------
    def _save_queue(self) -> None:
        try:
            payload = [
                {
                    "mission_id": q.mission_id,
                    "request": q.request,
                    "priority": q.priority.value
                    if isinstance(q.priority, MissionPriority)
                    else str(q.priority),
                    "risk_level": q.risk_level,
                    "submitted_at": q.submitted_at,
                }
                for q in self._queue
            ]
            self._queue_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed saving daemon queue: %s", e)

    def _load_queue(self) -> None:
        if not self._queue_file.exists():
            return
        try:
            payload = json.loads(self._queue_file.read_text(encoding="utf-8"))
            for item in payload:
                try:
                    prio = MissionPriority(item.get("priority", "normal"))
                except Exception:
                    prio = MissionPriority.NORMAL
                self._queue.append(
                    QueuedMission(
                        mission_id=item.get("mission_id", f"m-{uuid.uuid4().hex[:6]}"),
                        request=item.get("request", ""),
                        priority=prio,
                        risk_level=item.get("risk_level", "medium"),
                        submitted_at=item.get("submitted_at", time.time()),
                    )
                )
        except Exception as e:
            logger.debug("Failed loading daemon queue: %s", e)

    def requeue_interrupted(self) -> list[str]:
        """Re-enqueue missions that were in_progress at shutdown. Returns mission_ids."""
        interrupted = self.reconstruct_from_crash()
        requeued: list[str] = []
        for snap in interrupted:
            if any(q.request == snap.objective for q in self._queue):
                continue
            mid = self.enqueue_mission(
                snap.objective, priority=MissionPriority.HIGH, risk_level="medium"
            )
            requeued.append(mid)
            snap.status = "in_progress"
        return requeued

    def _acquire_pid_lock(self) -> bool:
        try:
            if self._pid_file.exists():
                try:
                    old_pid = int(self._pid_file.read_text(encoding="utf-8").strip())
                    if old_pid == os.getpid():
                        return True
                    alive: Optional[bool] = None
                    try:
                        import psutil  # type: ignore

                        alive = psutil.pid_exists(old_pid)
                    except Exception:
                        alive = None
                    if alive is False:
                        logger.warning("Stale daemon pid file (pid=%s dead); taking over.", old_pid)
                    elif alive is True:
                        logger.warning(
                            "Another daemon holds the lock (pid=%s); refusing second instance.",
                            old_pid,
                        )
                        return False
                    else:
                        logger.warning(
                            "Existing daemon pid file found (pid=%s); continuing single-instance.",
                            old_pid,
                        )
                except Exception:
                    pass
            self._pid_file.write_text(str(os.getpid()), encoding="utf-8")
            return True
        except Exception as e:
            logger.debug("PID lock failed: %s", e)
            return True

    def _release_pid_lock(self) -> None:
        try:
            if self._pid_file.exists():
                self._pid_file.unlink()
        except Exception:
            pass

    def request_stop(self) -> None:
        """Ask a running loop to stop gracefully (also honored across restarts via stop file)."""
        self._stop_requested = True
        try:
            self._stop_file.write_text(json.dumps({"requested_at": time.time()}), encoding="utf-8")
        except Exception:
            pass

    def clear_stop(self) -> None:
        self._stop_requested = False
        try:
            if self._stop_file.exists():
                self._stop_file.unlink()
        except Exception:
            pass

    def _stop_signalled(self) -> bool:
        return self._stop_requested or self._stop_file.exists()

    async def run_forever(
        self,
        mission_runner: Callable[[QueuedMission], Awaitable[Dict[str, Any]]],
        poll_interval_seconds: float = 2.0,
        max_iterations: Optional[int] = None,
        max_consecutive_failures: int = 5,
        on_tick: Optional[Callable[[int], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """Continuously drain the queue until stop is requested.

        mission_runner: async callable receiving QueuedMission, returning result dict
            with at least a 'status' key ('completed' on success).
        Bounded runs (max_iterations set) exit with status 'idle' after a
        grace period on an empty queue instead of hanging forever.
        """
        if not self._acquire_pid_lock():
            return {
                "status": "locked",
                "completed": 0,
                "failed": 0,
                "iterations": self._iterations_completed,
                "elapsed_seconds": 0.0,
                "pending": self.pending_count(),
            }
        self.clear_stop()
        self._is_running = True
        self.requeue_interrupted()
        completed = 0
        failed = 0
        idle_polls = 0
        started_at = time.time()
        logger.info(
            "Daemon 24/7 loop started (poll=%.1fs, max_iter=%s)",
            poll_interval_seconds,
            max_iterations,
        )
        try:
            while not self._stop_signalled():
                if max_iterations is not None and self._iterations_completed >= max_iterations:
                    break
                mission = self.pop_next_mission()
                if mission is None:
                    idle_polls += 1
                    if on_tick is not None:
                        try:
                            await on_tick(self._iterations_completed)
                        except Exception as e:
                            logger.debug("on_tick failed: %s", e)
                    if max_iterations is not None and idle_polls >= 3:
                        logger.info("Daemon idle with empty queue; bounded run exits.")
                        break
                    await asyncio.sleep(poll_interval_seconds)
                    continue
                idle_polls = 0
                snap = CheckpointSnapshot(
                    checkpoint_id=f"chk-{mission.mission_id}",
                    mission_id=mission.mission_id,
                    objective=mission.request,
                    completed_steps=[],
                    pending_steps=["step-1"],
                    state_registers={"risk_level": mission.risk_level},
                    world_state_summary="Daemon dispatched",
                    tokens_consumed=0,
                    status="in_progress",
                )
                self.save_checkpoint(snap)
                try:
                    result = await mission_runner(mission)
                    status = str(result.get("status", "completed"))
                    snap.status = "completed" if status == "completed" else "failed"
                    snap.completed_steps = [status]
                    snap.pending_steps = []
                    self.save_checkpoint(snap)
                    if snap.status == "completed":
                        completed += 1
                        self._consecutive_failures = 0
                    else:
                        failed += 1
                        self._consecutive_failures += 1
                except Exception as e:
                    import traceback as _tb

                    tb = _tb.format_exc(limit=8)
                    logger.exception("Daemon mission %s crashed: %s", mission.mission_id, e)
                    snap.status = "failed"
                    snap.completed_steps = [f"crash: {e}"]
                    snap.pending_steps = [mission.request]
                    snap.state_registers = {**snap.state_registers, "traceback": tb[-2000:]}
                    self.save_checkpoint(snap)
                    failed += 1
                    self._consecutive_failures += 1
                self._iterations_completed += 1
                if self._consecutive_failures >= max_consecutive_failures:
                    logger.error(
                        "Daemon aborting: %d consecutive failures", self._consecutive_failures
                    )
                    break
            if self._stop_signalled():
                final = "stopped"
            elif max_iterations is not None and self._iterations_completed == 0:
                final = "idle"
            else:
                final = "completed"
            return {
                "status": final,
                "completed": completed,
                "failed": failed,
                "iterations": self._iterations_completed,
                "elapsed_seconds": round(time.time() - started_at, 2),
                "pending": self.pending_count(),
            }
        finally:
            self._is_running = False
            self._release_pid_lock()

    def run_forever_sync(
        self,
        mission_runner: Callable[[QueuedMission], Awaitable[Dict[str, Any]]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return asyncio.run(self.run_forever(mission_runner, **kwargs))

    def stats(self) -> Dict[str, Any]:
        return {
            "is_running": self._is_running,
            "pending": self.pending_count(),
            "checkpoints": self.active_checkpoints_count(),
            "iterations_completed": self._iterations_completed,
            "consecutive_failures": self._consecutive_failures,
            "in_progress": len(self.reconstruct_from_crash()),
        }
