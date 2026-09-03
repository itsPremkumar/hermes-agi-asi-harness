"""
Hermes AGI/ASI Harness — Overnight Git Manager.

Provides robust, cross-platform Git operations for autonomous overnight loops:
- Clean tree verification
- Branch creation and switching
- Atomic commits on success
- Hard rollback (`git reset --hard`) on failure
- Diff statistics generation
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.overnight.git")


class GitManager:
    """Manages Git isolation, commits, and rollbacks for overnight autonomous iterations."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.git_bin = shutil.which("git") or "git"

    def _run_git(self, args: list[str], check: bool = False) -> subprocess.CompletedProcess:
        """Run a git command with UTF-8 encoding and timeout."""
        cmd = [self.git_bin] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if check and res.returncode != 0:
                raise RuntimeError(f"Git command failed ({' '.join(args)}): {res.stderr}")
            return res
        except Exception as e:
            logger.debug("Git command exception (%s): %s", " ".join(args), e)
            raise

    def is_git_repo(self) -> bool:
        """Check if workspace is inside a valid git repository."""
        try:
            res = self._run_git(["rev-parse", "--is-inside-work-tree"])
            return res.returncode == 0 and "true" in res.stdout.lower()
        except Exception:
            return False

    def is_clean(self) -> bool:
        """Check if the git working tree has no uncommitted changes."""
        try:
            res = self._run_git(["status", "--porcelain"])
            if res.returncode != 0:
                return False
            # Filter out ignored/untracked non-critical run metadata
            lines = [
                line for line in res.stdout.splitlines()
                if not line.strip().endswith(".json") and ".hermes" not in line and ".gnhf" not in line
            ]
            return len(lines) == 0
        except Exception:
            return False

    def get_current_branch(self) -> str:
        """Return the current branch name."""
        try:
            res = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
            return res.stdout.strip() if res.returncode == 0 else "main"
        except Exception:
            return "main"

    def create_and_checkout_branch(self, branch_name: str) -> bool:
        """Create a new branch from current HEAD and check it out."""
        try:
            res = self._run_git(["checkout", "-b", branch_name])
            return res.returncode == 0
        except Exception:
            return False

    def checkout_branch(self, branch_name: str) -> bool:
        """Switch to an existing branch."""
        try:
            res = self._run_git(["checkout", branch_name])
            return res.returncode == 0
        except Exception:
            return False

    def commit(self, message: str, add_all: bool = True) -> bool:
        """Stage changes and create an atomic commit without GPG signing prompts."""
        try:
            if add_all:
                self._run_git(["add", "-A"])
            res = self._run_git(["commit", "--no-gpg-sign", "-m", message])
            return res.returncode == 0
        except Exception:
            return False

    def hard_reset(self) -> bool:
        """Perform hard reset to discard any uncommitted or broken changes."""
        try:
            res1 = self._run_git(["reset", "--hard", "HEAD"])
            # Clean untracked files (excluding .hermes / state)
            res2 = self._run_git(["clean", "-fd", "-e", ".hermes*", "-e", "state*"])
            return res1.returncode == 0 and res2.returncode == 0
        except Exception:
            return False

    def has_changes(self) -> bool:
        """Check if there are any staged or unstaged changes."""
        try:
            res = self._run_git(["status", "--porcelain"])
            return bool(res.stdout.strip())
        except Exception:
            return False

    def get_diff_stats(self, base_branch: str) -> str:
        """Get git diff stats comparing current branch against base branch."""
        try:
            res = self._run_git(["diff", f"{base_branch}...HEAD", "--stat"])
            return res.stdout.strip() if res.returncode == 0 else "No diff statistics available."
        except Exception:
            return "Unable to compute diff stats."

    def get_recent_commits(self, count: int = 5) -> list[str]:
        """Get recent commit subjects on current branch."""
        try:
            res = self._run_git(["log", f"-n{count}", "--oneline"])
            return res.stdout.splitlines() if res.returncode == 0 else []
        except Exception:
            return []
