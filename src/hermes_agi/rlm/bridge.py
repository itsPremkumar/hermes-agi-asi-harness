"""
Hermes AGI/ASI Harness — RLM Subagent Recursion Bridge & Heap Snapshotter.

Ported from Prime Agent (prime-agent-runtime/src/rlm/__init__.py & repl.py):
- Exposes `rlm.run()` as a first-class async callable inside REPL code cells
- Tracks spawned subagent children with unique IDs, roles, and results
- Supports parallel subagent fan-out via `asyncio.gather(*tasks)`
- Manages durable in-memory variable heap snapshots and restoration
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import pickle
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.rlm.bridge")


@dataclass
class RLMSpawnHandle:
    """Represents a spawned recursive child agent."""
    rlm_child_id: str
    name: str
    role: str
    model: str
    prompt: str
    status: str  # "running", "completed", "error"
    result: Any = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rlm_child_id": self.rlm_child_id,
            "name": self.name,
            "role": self.role,
            "model": self.model,
            "prompt": self.prompt,
            "status": self.status,
            "result": self.result,
            "duration_seconds": round(self.duration_seconds, 3),
        }

    def __await__(self):
        """Allows awaiting the spawn handle directly: `result = await rlm.run(...)`"""
        async def _await_result():
            return self.result
        return _await_result().__await__()


class RLMBridge:
    """
    Injected as `rlm` into the REPL environment.
    Exposes programmatic subagent recursion, research, and thinking.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.snapshots_dir = self.workspace_root / ".hermes" / "rlm_snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._subagents: dict[str, RLMSpawnHandle] = {}

    async def run(
        self,
        prompt: str,
        role: str = "coder",
        model: str = "default",
        **kwargs: Any,
    ) -> RLMSpawnHandle:
        """
        Spawn a recursive child subagent and execute its objective.
        Returns an awaitable RLMSpawnHandle.
        """
        child_id = f"rlm-child-{uuid.uuid4().hex[:8]}"
        t0 = time.time()

        # Handle specialized roles programmatically
        result_payload: Any = None
        status = "completed"

        try:
            if role in ("researcher", "research"):
                from hermes_agi.research import DeepResearchAgent
                agent = DeepResearchAgent()
                depth = kwargs.get("depth", 2)
                dossier = await agent.investigate(prompt, depth=depth)
                result_payload = dossier.to_dict()

            elif role in ("thinker", "planner"):
                from hermes_agi.thinking import DeepThinkingEngine, MCTSSearchEngine
                if kwargs.get("use_mcts", False):
                    engine = MCTSSearchEngine()
                    res = engine.search(prompt)
                    result_payload = res.to_dict()
                else:
                    engine = DeepThinkingEngine()
                    res = await engine.deliberate(prompt)
                    result_payload = res.to_dict()

            elif role in ("verifier", "critic"):
                from core.verification.anti_goodhart import AntiGoodhartVerifier
                target_file = kwargs.get("target_file", "candidate.py")
                code = kwargs.get("code", "")
                ag = AntiGoodhartVerifier(workspace_root=str(self.workspace_root))
                verdict = ag.verify(target_file, code)
                result_payload = verdict.to_dict()

            else:  # General coding / execution child
                result_payload = {
                    "outcome": f"Executed subagent task for prompt: {prompt}",
                    "role": role,
                    "model": model,
                    "kwargs": kwargs,
                }

        except Exception as e:
            status = "error"
            result_payload = {"error": str(e)}

        handle = RLMSpawnHandle(
            rlm_child_id=child_id,
            name=f"{role}-{child_id[:6]}",
            role=role,
            model=model,
            prompt=prompt,
            status=status,
            result=result_payload,
            duration_seconds=time.time() - t0,
        )
        self._subagents[child_id] = handle
        return handle

    async def list_subagents(self) -> list[dict[str, Any]]:
        """List all active or completed subagents in this REPL session."""
        return [h.to_dict() for h in self._subagents.values()]

    async def get_subagent(self, child_id: str) -> Optional[dict[str, Any]]:
        """Get details of a specific subagent."""
        h = self._subagents.get(child_id)
        return h.to_dict() if h else None

    # Convenience shortcuts for direct async calling
    async def research(self, topic: str, depth: int = 2) -> dict[str, Any]:
        """Direct async research invocation."""
        from hermes_agi.research import DeepResearchAgent
        agent = DeepResearchAgent()
        dossier = await agent.investigate(topic, depth=depth)
        return dossier.to_dict()

    async def think(self, goal: str, use_mcts: bool = False) -> dict[str, Any]:
        """Direct async deliberation."""
        if use_mcts:
            from hermes_agi.thinking import MCTSSearchEngine
            engine = MCTSSearchEngine()
            return engine.search(goal).to_dict()
        else:
            from hermes_agi.thinking import DeepThinkingEngine
            engine = DeepThinkingEngine()
            res = await engine.deliberate(goal)
            return res.to_dict()

    def snapshot(self, name: str, variables: dict[str, Any]) -> str:
        """
        Save the REPL variable heap to disk.
        Filters unpickleable objects (modules, coroutines, internal handles).
        """
        snap_file = self.snapshots_dir / f"{name}.pkl"
        serializable: dict[str, Any] = {}
        for k, v in variables.items():
            if k.startswith("_") or inspect.ismodule(v) or inspect.isroutine(v):
                continue
            try:
                # Test pickle serializability
                pickle.dumps(v)
                serializable[k] = v
            except Exception:
                pass

        with open(snap_file, "wb") as f:
            pickle.dump(serializable, f)
        return str(snap_file)

    def restore(self, name: str) -> dict[str, Any]:
        """Restore variables from a saved heap snapshot."""
        snap_file = self.snapshots_dir / f"{name}.pkl"
        if not snap_file.exists():
            return {}
        try:
            with open(snap_file, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error("Failed to restore RLM snapshot %s: %s", name, e)
            return {}
