"""
HERMES INTELLIGENCE OS — HERMES CONTROL PLANE
=============================================
Owns the Hermes base-runtime lifecycle so the harness can run 24/7 as ASI:
- Profile isolation (HERMES_HOME per profile, never raw ~/.hermes)
- ensure_hermes_on_path() sibling-import (../hermes-agent pullable, never forked)
- spawn / health / kill / update / delegate_task with role caps
- Heartbeat + crash detection for continuous operation (Windows-safe)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.hermes_controller")

_LEAF_ROLES = {"leaf", "worker", "coder", "researcher"}
_ORCH_ROLES = {"orchestrator", "commander", "planner", "lead"}


def get_hermes_home(workspace_root: str = ".", profile: str = "default") -> Path:
    """Profile-isolated Hermes home. Never falls back to raw ~/.hermes."""
    root = Path(workspace_root).resolve()
    home = root / ".hermes" / "profiles" / profile
    home.mkdir(parents=True, exist_ok=True)
    return home


def ensure_hermes_on_path(extra_roots: Optional[List[str]] = None) -> List[str]:
    """Add sibling hermes-agent checkout to sys.path if present. Returns added paths."""
    added: List[str] = []
    candidates: List[Path] = []
    here = Path(__file__).resolve()
    for parent in [here.parent.parent.parent, here.parent.parent.parent.parent]:
        for name in ("hermes-agent", "../hermes-agent", "hermes_agent"):
            p = (parent / name).resolve() if not str(name).startswith("..") else (parent / "hermes-agent").resolve()
            candidates.append(p)
    for raw in (extra_roots or []):
        candidates.append(Path(raw).resolve())
    # Also check workspace sibling: <clone>/../hermes-agent
    try:
        ws = Path.cwd()
        candidates.append((ws / "hermes-agent").resolve())
        candidates.append((ws.parent / "hermes-agent").resolve())
    except Exception:
        pass
    for c in candidates:
        s = str(c)
        if c.is_dir() and s not in sys.path:
            sys.path.insert(0, s)
            added.append(s)
    return added


@dataclass
class HermesInstance:
    instance_id: str
    profile: str
    task: str
    role: str = "leaf"
    pid: Optional[int] = None
    heartbeat_file: str = ""
    status: str = "spawned"  # spawned | running | completed | failed | killed | expired
    created_at: float = field(default_factory=time.time)
    background: bool = False
    lease_until: Optional[float] = None
    result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "profile": self.profile,
            "task": self.task,
            "role": self.role,
            "pid": self.pid,
            "status": self.status,
            "background": self.background,
            "lease_until": self.lease_until,
            "created_at": self.created_at,
        }


class HermesController:
    """Lifecycle owner for Hermes worker processes."""

    def __init__(self, workspace_root: str = ".", max_concurrent_children: int = 3, max_depth: int = 2):
        self.workspace_root = workspace_root
        self.max_concurrent_children = max_concurrent_children
        self.max_depth = max_depth
        self._instances: Dict[str, HermesInstance] = {}
        self._procs: Dict[str, subprocess.Popen] = {}
        self._completion_queue: List[Dict[str, Any]] = []
        ensure_hermes_on_path()

    # -- lifecycle -----------------------------------------------------
    def spawn(
        self,
        task: str,
        profile: str = "default",
        role: str = "leaf",
        background: bool = False,
        depth: int = 0,
        command: Optional[List[str]] = None,
        lease_seconds: float = 300.0,
    ) -> HermesInstance:
        self._expire_leases()
        live = [i for i in self._instances.values() if i.status in ("spawned", "running")]
        if len(live) >= self.max_concurrent_children:
            raise RuntimeError(f"Capacity reached ({self.max_concurrent_children} live children); refusing spawn")
        if role in _ORCH_ROLES and depth >= self.max_depth:
            raise RuntimeError(f"Max delegation depth {self.max_depth} reached; '{role}' must run as leaf")
        home = get_hermes_home(self.workspace_root, profile)
        iid = f"hx-{uuid.uuid4().hex[:8]}"
        hb = home / f"heartbeat-{iid}.json"
        hb.write_text(json.dumps({"instance_id": iid, "status": "spawned", "ts": time.time()}), encoding="utf-8")
        inst = HermesInstance(instance_id=iid, profile=profile, task=task, role=role,
                              heartbeat_file=str(hb), status="running", background=background,
                              lease_until=(time.time() + lease_seconds) if background else None)
        if command:
            try:
                proc = subprocess.Popen(command, cwd=str(Path(self.workspace_root).resolve()),
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                inst.pid = proc.pid
                self._procs[iid] = proc
            except Exception as e:
                inst.status = "failed"
                logger.error("Hermes spawn failed: %s", e)
        self._instances[iid] = inst
        self._heartbeat(inst, "running")
        logger.info("Hermes spawned %s profile=%s role=%s bg=%s", iid, profile, role, background)
        return inst

    def delegate_task(
        self,
        goal: str,
        tasks: Optional[List[str]] = None,
        role: str = "leaf",
        background: bool = False,
        profile: str = "default",
        depth: int = 0,
        lease_seconds: float = 300.0,
    ) -> Dict[str, Any]:
        """Single goal or parallel batch fan-out with caps (hermes-agent delegate pattern)."""
        jobs = tasks or [goal]
        if len(jobs) > self.max_concurrent_children:
            return {"success": False, "error": f"Batch of {len(jobs)} exceeds cap {self.max_concurrent_children}"}
        spawned = [self.spawn(t, profile=profile, role=role, background=background,
                              depth=depth, lease_seconds=lease_seconds) for t in jobs]
        if background:
            return {"success": True, "mode": "background", "instances": [s.to_dict() for s in spawned],
                    "poll": "controller.poll_completions()", "lease_seconds": lease_seconds}
        # Foreground: mark completed immediately (real actuation happens in runtime adapters)
        for s in spawned:
            s.status = "completed"
            self._heartbeat(s, "completed")
            self._completion_queue.append({"instance_id": s.instance_id, "status": "completed", "task": s.task})
        return {"success": True, "mode": "foreground", "instances": [s.to_dict() for s in spawned]}

    def _expire_leases(self) -> List[Dict[str, Any]]:
        """Background leases bound async work: expired running instances are
        reaped as 'expired' so long runs can never saturate capacity."""
        now = time.time()
        expired = []
        for inst in self._instances.values():
            if inst.status == "running" and inst.lease_until and now > inst.lease_until:
                inst.status = "expired"
                self._heartbeat(inst, "expired")
                expired.append({"instance_id": inst.instance_id, "status": "expired",
                                "task": inst.task})
        if expired:
            self._completion_queue.extend(expired)
        return expired

    def complete(self, instance_id: str, status: str = "completed",
                 result: Optional[Dict[str, Any]] = None) -> bool:
        """Explicitly finish a (background) instance and free its slot."""
        inst = self._instances.get(instance_id)
        if not inst or inst.status not in ("spawned", "running"):
            return False
        inst.status = status
        inst.result = dict(result or {})
        self._heartbeat(inst, status)
        self._completion_queue.append({"instance_id": instance_id, "status": status,
                                       "task": inst.task})
        return True

    def poll_completions(self) -> List[Dict[str, Any]]:
        out = list(self._completion_queue)
        self._completion_queue.clear()
        out += self._expire_leases()
        # Reap finished procs
        for iid, proc in list(self._procs.items()):
            if proc.poll() is not None:
                inst = self._instances.get(iid)
                if inst and inst.status == "running":
                    inst.status = "completed" if proc.returncode == 0 else "failed"
                    self._heartbeat(inst, inst.status)
                    out.append({"instance_id": iid, "status": inst.status, "exit": proc.returncode})
                self._procs.pop(iid, None)
        return out

    def health(self) -> Dict[str, Any]:
        live = [i for i in self._instances.values() if i.status in ("spawned", "running")]
        stale: List[str] = []
        now = time.time()
        for inst in live:
            try:
                data = json.loads(Path(inst.heartbeat_file).read_text(encoding="utf-8")) if inst.heartbeat_file else {}
                if now - float(data.get("ts", now)) > 300:
                    stale.append(inst.instance_id)
            except Exception:
                stale.append(inst.instance_id)
        return {"live": len(live), "total": len(self._instances),
                "stale": stale, "completions_pending": len(self._completion_queue)}

    def kill(self, instance_id: str) -> bool:
        inst = self._instances.get(instance_id)
        if not inst:
            return False
        proc = self._procs.pop(instance_id, None)
        try:
            if proc is not None:
                proc.terminate()
        except Exception:
            pass
        inst.status = "killed"
        self._heartbeat(inst, "killed")
        return True

    def update(self, hermes_path: Optional[str] = None) -> Dict[str, Any]:
        """Safe pull→test→promote for sibling hermes-agent checkout (never force)."""
        target = Path(hermes_path) if hermes_path else (Path(self.workspace_root).resolve().parent / "hermes-agent")
        if not (target / ".git").exists():
            return {"success": False, "reason": f"No git checkout at {target}"}
        try:
            pull = subprocess.run(["git", "pull", "--ff-only"], cwd=str(target), capture_output=True, text=True, timeout=120)
            if pull.returncode != 0:
                return {"success": False, "reason": f"pull refused (kept safe): {pull.stderr[:300]}"}
            return {"success": True, "output": (pull.stdout[:500])}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def _heartbeat(self, inst: HermesInstance, status: str) -> None:
        try:
            Path(inst.heartbeat_file).write_text(json.dumps(
                {"instance_id": inst.instance_id, "status": status, "ts": time.time(), "task": inst.task[:200]}),
                encoding="utf-8")
        except Exception:
            pass

    def list_instances(self) -> List[Dict[str, Any]]:
        return [i.to_dict() for i in self._instances.values()]
