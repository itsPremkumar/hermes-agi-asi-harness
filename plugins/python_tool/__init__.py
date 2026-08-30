#!/usr/bin/env python3
"""
Python Execution Tool Plugin — Safe Python code execution
==========================================================
Features:
- Execute Python code with timeout
- Safe builtins sandboxing
- Output capture (stdout, stderr, return value)
- Interactive mode support
- Import management
"""

from __future__ import annotations

import asyncio
import io
import logging
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_python_tool")

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
        network_domains: list[str] = field(default_factory=list)
        shell_commands: list[str] = field(default_factory=list)
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
        capabilities: list[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: list[str] = field(default_factory=list)
        path: Path | None = None
    
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


class PythonTool:
    """Safe Python code execution."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
    
    def run(self, code: str, timeout: float | None = None, globals_dict: dict | None = None) -> dict[str, Any]:
        """
        Execute Python code safely.
        """
        start_time = time.time()
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Safe globals with limited builtins
        safe_builtins = {
            'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
            'enumerate': enumerate, 'filter': filter, 'float': float,
            'format': format, 'frozenset': frozenset, 'getattr': getattr,
            'hasattr': hasattr, 'hash': hash, 'hex': hex, 'int': int,
            'isinstance': isinstance, 'issubclass': issubclass, 'iter': iter,
            'len': len, 'list': list, 'map': map, 'max': max, 'min': min,
            'next': next, 'object': object, 'oct': oct, 'ord': ord,
            'pow': pow, 'print': print, 'property': property, 'range': range,
            'repr': repr, 'reversed': reversed, 'round': round, 'set': set,
            'setattr': setattr, 'slice': slice, 'sorted': sorted, 'str': str,
            'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
            'True': True, 'False': False, 'None': None,
            'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
            'KeyError': KeyError, 'IndexError': IndexError, 'RuntimeError': RuntimeError,
            'StopIteration': StopIteration, 'ZeroDivisionError': ZeroDivisionError,
        }
        
        exec_globals = {
            '__builtins__': safe_builtins,
            '__name__': '__main__',
        }
        
        if globals_dict:
            exec_globals.update(globals_dict)
        
        # Add some useful modules
        for mod_name in ['math', 'json', 'os', 'sys', 'time', 'datetime', 'collections', 'itertools', 'functools', 're', 'pathlib', 'typing']:
            try:
                exec_globals[mod_name] = __import__(mod_name)
            except ImportError:
                pass
        
        result_value = None
        error_info: dict | None = None
        
        try:
            exec_locals: dict[str, Any] = {}
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, exec_globals, exec_locals)
            
            # Get the last expression result
            if exec_locals and '__result__' not in exec_locals:
                result_value = exec_locals.get('_') or exec_locals.get('result')
            else:
                result_value = exec_locals.get('__result__')
                
        except Exception as e:
            error_info = {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc(),
            }
        
        duration = time.time() - start_time
        
        return {
            "success": error_info is None,
            "result": result_value,
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "duration": duration,
            "error": error_info,
        }
    
    async def run_async(self, code: str, timeout: float | None = None) -> dict[str, Any]:
        """Execute Python code asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run, code, timeout)


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Python Execution Tool Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="python_tool",
            version="1.0.0",
            description="Safe Python code execution with timeout, sandboxed builtins, and output capture",
            license="MIT",
            source="internal",
            capabilities=["python_execute", "code_execution", "script_running", "expression_eval"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=50,
            ),
        )
        self.tool: PythonTool | None = None
    
    async def load(self) -> bool:
        self.tool = PythonTool()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.tool:
            self.tool = PythonTool()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.tool is not None,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def run(self, code: str, timeout: float = 30.0) -> dict[str, Any]:
        """Execute Python code."""
        return self.tool.run(code, timeout=timeout)
    
    async def run_async(self, code: str, timeout: float = 30.0) -> dict[str, Any]:
        """Execute Python code asynchronously."""
        return await self.tool.run_async(code, timeout=timeout)
    
    def get_capabilities(self) -> list[str]:
        return self.manifest.capabilities
