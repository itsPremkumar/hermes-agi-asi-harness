#!/usr/bin/env python3
"""
Git Tool Plugin — Git repository operations
==========================================
Features:
- Clone, init, status, add, commit, push, pull
- Branch management
- Diff viewing
- Log retrieval
- Safe operation with error handling
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_git_tool")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


@dataclass
class GitResult:
    """Result of a git operation."""
    command: str
    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration: float


class GitTool:
    """Git repository operations."""
    
    def __init__(self, cwd: str = ".", timeout: int = 120):
        self.cwd = Path(cwd)
        self.timeout = timeout
    
    def _run_git(self, args: List[str], check: bool = True) -> GitResult:
        """Run a git command."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            duration = time.time() - start_time
            
            return GitResult(
                command="git " + " ".join(args),
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return GitResult(
                command="git " + " ".join(args),
                success=False,
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                return_code=-1,
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return GitResult(
                command="git " + " ".join(args),
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                duration=duration,
            )
    
    def init(self) -> Dict[str, Any]:
        """Initialize a git repository."""
        result = self._run_git(["init"])
        return self._to_dict(result)
    
    def status(self) -> Dict[str, Any]:
        """Get git status."""
        result = self._run_git(["status", "--porcelain=v1", "-b"], check=False)
        
        if not result.success:
            return self._to_dict(result)
        
        # Parse porcelain output
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        branch = "unknown"
        files: List[Dict[str, str]] = []
        
        for line in lines:
            if line.startswith("##"):
                # Branch line
                branch_info = line[3:].strip()
                if "..." in branch_info:
                    branch = branch_info.split("...")[0]
                else:
                    branch = branch_info
                continue
            
            if len(line) >= 2:
                status_code = line[:2]
                filename = line[3:]
                files.append({
                    "status": status_code,
                    "filename": filename,
                    "staged": status_code[0] != " " and status_code[0] != "?",
                    "modified": status_code[1] != " ",
                })
        
        return {
            "success": True,
            "branch": branch,
            "files": files,
            "clean": len(files) == 0,
            "raw": result.stdout,
        }
    
    def add(self, paths: List[str]) -> Dict[str, Any]:
        """Stage files."""
        if not paths:
            paths = ["."]
        result = self._run_git(["add"] + paths)
        return self._to_dict(result)
    
    def commit(self, message: str, author: Optional[str] = None) -> Dict[str, Any]:
        """Commit staged changes."""
        args = ["commit", "-m", message]
        if author:
            args.extend(["--author", author])
        result = self._run_git(args)
        return self._to_dict(result)
    
    def push(self, remote: str = "origin", branch: str = "", force: bool = False) -> Dict[str, Any]:
        """Push to remote."""
        args = ["push"]
        if force:
            args.append("--force")
        if remote:
            args.append(remote)
        if branch:
            args.append(branch)
        result = self._run_git(args)
        return self._to_dict(result)
    
    def pull(self, remote: str = "origin", branch: str = "", rebase: bool = False) -> Dict[str, Any]:
        """Pull from remote."""
        args = ["pull"]
        if rebase:
            args.append("--rebase")
        if remote:
            args.append(remote)
        if branch:
            args.append(branch)
        result = self._run_git(args)
        return self._to_dict(result)
    
    def clone(self, url: str, dest: str = ".") -> Dict[str, Any]:
        """Clone a repository."""
        result = self._run_git(["clone", url, dest])
        return self._to_dict(result)
    
    def branch(self, name: Optional[str] = None, delete: bool = False) -> Dict[str, Any]:
        """Branch operations."""
        if delete and name:
            result = self._run_git(["branch", "-D", name])
        elif name:
            result = self._run_git(["branch", name])
        else:
            result = self._run_git(["branch", "-a"], check=False)
            if result.success:
                branches = [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]
                return {"success": True, "branches": branches}
            return self._to_dict(result)
        return self._to_dict(result)
    
    def checkout(self, target: str, create_branch: bool = False) -> Dict[str, Any]:
        """Checkout a branch or commit."""
        args = ["checkout"]
        if create_branch:
            args.append("-b")
        args.append(target)
        result = self._run_git(args)
        return self._to_dict(result)
    
    def diff(self, staged: bool = False, file: Optional[str] = None) -> Dict[str, Any]:
        """Get diff."""
        args = ["diff"]
        if staged:
            args.append("--cached")
        if file:
            args.append(file)
        result = self._run_git(args, check=False)
        return {
            "success": result.success,
            "diff": result.stdout,
            "error": result.stderr if not result.success else None,
        }
    
    def log(self, limit: int = 20, oneline: bool = True) -> Dict[str, Any]:
        """Get commit log."""
        args = ["log"]
        if oneline:
            args.append("--oneline")
        args.extend(["-n", str(limit)])
        
        result = self._run_git(args, check=False)
        if result.success:
            commits = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
            return {"success": True, "commits": commits, "count": len(commits)}
        return self._to_dict(result)
    
    def is_repo(self) -> bool:
        """Check if current directory is a git repository."""
        result = self._run_git(["rev-parse", "--is-inside-work-tree"], check=False)
        return result.success and result.stdout.strip() == "true"
    
    def _to_dict(self, result: GitResult) -> Dict[str, Any]:
        return {
            "success": result.success,
            "command": result.command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "duration": result.duration,
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Git Tool Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="git_tool",
            version="1.0.0",
            description="Git repository operations with safe error handling and porcelain parsing",
            license="MIT",
            source="internal",
            capabilities=["git_init", "git_status", "git_add", "git_commit", "git_push", "git_pull", "git_clone", "git_branch", "git_checkout", "git_diff", "git_log"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=["github.com", "gitlab.com"],
                shell_commands=["git"],
                secrets_access="none",
                max_memory_mb=256,
                max_cpu_percent=20,
            ),
        )
        self.tool: Optional[GitTool] = None
    
    async def load(self) -> bool:
        self.tool = GitTool()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.tool:
            self.tool = GitTool()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.tool is not None,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def init(self) -> Dict[str, Any]:
        return self.tool.init()
    
    def status(self) -> Dict[str, Any]:
        return self.tool.status()
    
    def add(self, paths: List[str] = None) -> Dict[str, Any]:
        return self.tool.add(paths or [])
    
    def commit(self, message: str, author: Optional[str] = None) -> Dict[str, Any]:
        return self.tool.commit(message, author)
    
    def push(self, remote: str = "origin", branch: str = "", force: bool = False) -> Dict[str, Any]:
        return self.tool.push(remote, branch, force)
    
    def pull(self, remote: str = "origin", branch: str = "", rebase: bool = False) -> Dict[str, Any]:
        return self.tool.pull(remote, branch, rebase)
    
    def clone(self, url: str, dest: str = ".") -> Dict[str, Any]:
        return self.tool.clone(url, dest)
    
    def branch(self, name: Optional[str] = None, delete: bool = False) -> Dict[str, Any]:
        return self.tool.branch(name, delete)
    
    def checkout(self, target: str, create_branch: bool = False) -> Dict[str, Any]:
        return self.tool.checkout(target, create_branch)
    
    def diff(self, staged: bool = False, file: Optional[str] = None) -> Dict[str, Any]:
        return self.tool.diff(staged, file)
    
    def log(self, limit: int = 20, oneline: bool = True) -> Dict[str, Any]:
        return self.tool.log(limit, oneline)
    
    def is_repo(self) -> bool:
        return self.tool.is_repo()
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
