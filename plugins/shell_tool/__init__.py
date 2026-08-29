#!/usr/bin/env python3
"""
Shell Tool Plugin — Safe shell command execution
================================================
Features:
- Run shell commands with timeout
- Working directory control
- Environment variable support
- Output capture (stdout/stderr)
- Exit code tracking
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_shell_tool")

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
        max_cpu_percent: 50
    
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
class ShellResult:
    """Result of a shell command."""
    command: str
    return_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None


class ShellTool:
    """
    Safe shell command execution.
    """
    
    def __init__(self, timeout: int = 60, cwd: str = "."):
        self.timeout = timeout
        self.cwd = Path(cwd)
    
    def run(self, command: str, timeout: int = None, env: Dict[str, str] = None) -> ShellResult:
        """
        Run a shell command.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds (overrides default)
            env: Additional environment variables
            
        Returns:
            ShellResult with output and metadata
        """
        start_time = time.time()
        
        try:
            # Merge environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                cwd=self.cwd,
                env=run_env,
            )
            
            duration = time.time() - start_time
            
            return ShellResult(
                command=command,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                success=result.returncode == 0,
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return ShellResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr="",
                duration_seconds=duration,
                success=False,
                error_message=f"Command timed out after {timeout or self.timeout}s",
            )
        except Exception as e:
            duration = time.time() - start_time
            return ShellResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration_seconds=duration,
                success=False,
                error_message=str(e),
            )
    
    async def run_async(self, command: str, timeout: int = None) -> ShellResult:
        """Run a shell command asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run, command, timeout)


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Shell Tool Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="shell_tool",
            version="1.0.0",
            description="Safe shell command execution with timeout and output capture",
            license="MIT",
            source="internal",
            capabilities=["shell_execution", "command_running", "subprocess_management"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=["*"],
                shell_commands=["*"],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=50,
            ),
        )
        self.tool: Optional[ShellTool] = None
    
    async def load(self) -> bool:
        self.tool = ShellTool()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.tool:
            self.tool = ShellTool()
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
    
    def run(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        """Run a shell command."""
        result = self.tool.run(command, timeout=timeout)
        return {
            "command": result.command,
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": result.duration_seconds,
            "success": result.success,
            "error": result.error_message,
        }
    
    async def run_async(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        """Run a shell command asynchronously."""
        result = await self.tool.run_async(command, timeout=timeout)
        return {
            "command": result.command,
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": result.duration_seconds,
            "success": result.success,
            "error": result.error_message,
        }
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
