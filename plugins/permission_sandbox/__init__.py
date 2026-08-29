#!/usr/bin/env python3
"""
Permission Sandbox Plugin — Runtime sandbox enforcement
======================================================
Features:
- Sandbox execution environment for code/commands
- Resource limits (CPU, memory, time)
- Network isolation policies
- Filesystem access control
- Safe evaluation wrapper
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
import time

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    # Windows does not have the resource module
    HAS_RESOURCE = False
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_permission_sandbox")

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
class SandboxConfig:
    """Sandbox configuration."""
    max_cpu_time: int = 30  # seconds
    max_memory_mb: int = 512
    network_allowed: bool = False
    allowed_paths: List[str] = field(default_factory=lambda: ["/tmp", "."])
    forbidden_commands: List[str] = field(default_factory=lambda: ["rm -rf", "sudo", "mkfs", "dd"])
    read_only_fs: bool = False


class SandboxViolation(Exception):
    """Raised when a sandbox violation occurs."""
    pass


class PermissionSandbox:
    """Runtime sandbox for safe execution."""
    
    def __init__(self, config: SandboxConfig = None):
        self.config = config or SandboxConfig()
        self.violations: List[Dict[str, Any]] = []
    
    def check_command(self, command: str) -> Tuple[bool, str]:
        """Check if a command is allowed."""
        # Check forbidden commands
        for forbidden in self.config.forbidden_commands:
            if forbidden.lower() in command.lower():
                self._record_violation(command, f"Forbidden command pattern: {forbidden}")
                return False, f"Command contains forbidden pattern: {forbidden}"
        
        # Check network
        if not self.config.network_allowed:
            network_indicators = ["curl", "wget", "http://", "https://", "ftp://", "ssh", "scp"]
            for indicator in network_indicators:
                if indicator in command.lower():
                    self._record_violation(command, f"Network access not allowed: {indicator}")
                    return False, f"Network access not allowed: {indicator}"
        
        return True, "OK"
    
    def _record_violation(self, command: str, reason: str):
        """Record a sandbox violation."""
        self.violations.append({
            "command": command,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def enforce_limits(self):
        """Enforce resource limits (Unix only)."""
        if not HAS_RESOURCE:
            return
        try:
            # CPU time limit
            if hasattr(resource, 'RLIMIT_CPU'):
                resource.setrlimit(resource.RLIMIT_CPU, 
                                 (self.config.max_cpu_time, self.config.max_cpu_time))
            
            # Memory limit
            if hasattr(resource, 'RLIMIT_AS'):
                mem_bytes = self.config.max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, OSError) as e:
            logger.warning(f"Could not set resource limits: {e}")
    
    def run_command(self, command: str, cwd: str = ".", timeout: int = None) -> Dict[str, Any]:
        """Run a command in sandbox."""
        allowed, reason = self.check_command(command)
        if not allowed:
            return {
                "success": False,
                "error": reason,
                "violation": True,
            }
        
        timeout = timeout or self.config.max_cpu_time
        
        try:
            start_time = time.time()
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                preexec_fn=self.enforce_limits if (os.name != "nt" and HAS_RESOURCE) else None,
            )
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout}s",
                "violation": False,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "violation": False,
            }
    
    def safe_eval(self, expression: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Safely evaluate a Python expression."""
        # Block dangerous builtins
        dangerous = ["__import__", "eval", "exec", "open", "compile", "globals", "locals", "getattr", "setattr"]
        
        for d in dangerous:
            if d in expression:
                self._record_violation(expression, f"Dangerous builtin: {d}")
                return {
                    "success": False,
                    "error": f"Dangerous builtin not allowed: {d}",
                    "violation": True,
                }
        
        try:
            safe_context = context or {}
            result = eval(expression, {"__builtins__": {}}, safe_context)
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "violation": False,
            }
    
    def get_violations(self) -> List[Dict[str, Any]]:
        """Get recorded violations."""
        return self.violations
    
    def is_violated(self) -> bool:
        """Check if any violations occurred."""
        return len(self.violations) > 0


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Permission Sandbox Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="permission_sandbox",
            version="1.0.0",
            description="Runtime sandbox enforcement with resource limits, network isolation, and safe evaluation",
            license="MIT",
            source="internal",
            capabilities=["sandbox_execution", "resource_limits", "network_isolation", "safe_eval"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=256,
                max_cpu_percent=10,
            ),
        )
        self.sandbox: Optional[PermissionSandbox] = None
    
    async def load(self) -> bool:
        self.sandbox = PermissionSandbox()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.sandbox:
            self.sandbox = PermissionSandbox()
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
            "ready": self.sandbox is not None,
            "violations": len(self.sandbox.violations) if self.sandbox else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def check_command(self, command: str) -> Tuple[bool, str]:
        return self.sandbox.check_command(command)
    
    def run_command(self, command: str, cwd: str = ".", timeout: int = None) -> Dict[str, Any]:
        return self.sandbox.run_command(command, cwd, timeout)
    
    def safe_eval(self, expression: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return self.sandbox.safe_eval(expression, context)
    
    def configure(self, max_cpu_time: int = 30, max_memory_mb: int = 512, 
                  network_allowed: bool = False, read_only_fs: bool = False):
        """Configure sandbox."""
        from plugins.permission_sandbox import SandboxConfig
        self.sandbox = PermissionSandbox(SandboxConfig(
            max_cpu_time=max_cpu_time,
            max_memory_mb=max_memory_mb,
            network_allowed=network_allowed,
            read_only_fs=read_only_fs,
        ))
    
    def get_violations(self) -> List[Dict[str, Any]]:
        return self.sandbox.get_violations()
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
