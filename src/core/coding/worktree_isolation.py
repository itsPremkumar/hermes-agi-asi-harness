"""Worktree Isolation — Git worktree per agent."""
from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Worktree:
    id: str
    agent_id: str
    branch: str
    path: str
    status: str = "active"
    created_at: float = 0.0

class WorktreeManager:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.worktrees: dict[str, Worktree] = {}
    
    def create_worktree(self, agent_id: str, branch: str) -> Worktree | None:
        worktree_path = self.repo_path / ".worktrees" / agent_id
        try:
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch],
                cwd=self.repo_path, capture_output=True, timeout=30
            )
            wt = Worktree(id=str(uuid.uuid4()), agent_id=agent_id,
                         branch=branch, path=str(worktree_path))
            self.worktrees[wt.id] = wt
            return wt
        except Exception:
            return None
    
    def remove_worktree(self, worktree_id: str):
        wt = self.worktrees.get(worktree_id)
        if wt:
            try:
                subprocess.run(
                    ["git", "worktree", "remove", wt.path],
                    cwd=self.repo_path, capture_output=True, timeout=30
                )
            except Exception:
                pass
            del self.worktrees[worktree_id]
    
    def get_state(self) -> dict[str, Any]:
        return {"worktrees": len(self.worktrees)}
