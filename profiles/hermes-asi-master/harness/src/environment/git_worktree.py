#!/usr/bin/env python3
"""
git_worktree.py — Git Worktree Isolation Manager for Concurrent Subagents
Enables zero-collision branch and filesystem isolation across multi-agent pipelines.
"""

import os
import shutil
import pathlib
import subprocess
from typing import List, Dict, Optional

class GitWorktreeManager:
    def __init__(self, base_worktree_dir: Optional[pathlib.Path] = None):
        self.base_dir = base_worktree_dir or (pathlib.Path.home() / ".hermes" / "worktrees")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_worktree(self, repo_path: pathlib.Path, branch_name: str) -> Optional[pathlib.Path]:
        target_dir = self.base_dir / branch_name
        if target_dir.exists():
            return target_dir

        cmd = ["git", "worktree", "add", "-b", branch_name, str(target_dir)]
        try:
            res = subprocess.run(cmd, cwd=str(repo_path), capture_output=True, text=True, check=True)
            return target_dir
        except Exception:
            # Fallback to copy directory if git worktree fails (e.g. not a git repo or branch exists)
            try:
                shutil.copytree(repo_path, target_dir, ignore=shutil.ignore_patterns(".git", "__pycache__"))
                return target_dir
            except Exception:
                return None

    def remove_worktree(self, repo_path: pathlib.Path, worktree_path: pathlib.Path):
        if not worktree_path.exists():
            return
        cmd = ["git", "worktree", "remove", "--force", str(worktree_path)]
        try:
            subprocess.run(cmd, cwd=str(repo_path), capture_output=True, text=True)
        except Exception:
            pass

        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)
