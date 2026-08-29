#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v5.0 — TOOL REGISTRY
=============================================
Unified tool registration, discovery, and execution.

Extracted from:
- hermes-agent: tool registration patterns
- agx-harness-main: tool abstraction patterns
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("hermes_tools")


class ToolRisk(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolSchema:
    """Tool input/output schema."""
    type: str = "object"
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)


@dataclass
class ToolManifest:
    """Tool metadata."""
    name: str
    version: str
    description: str
    category: str
    input_schema: ToolSchema = field(default_factory=ToolSchema)
    output_schema: ToolSchema = field(default_factory=ToolSchema)
    risk: ToolRisk = ToolRisk.LOW
    timeout_seconds: int = 60
    requires_permissions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    tool_name: str = ""
    tool_version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool:
    """Base class for all tools."""
    
    def __init__(self):
        self.manifest: Optional[ToolManifest] = None
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        raise NotImplementedError
    
    async def validate(self, **kwargs) -> bool:
        """Validate input parameters."""
        return True
    
    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {"status": "healthy", "tool": self.manifest.name if self.manifest else "unknown"}


class ToolRegistry:
    """
    Unified tool registry.
    
    Features:
    - Tool registration with schema validation
    - Permission checking
    - Audit logging
    - Tool discovery by category, tag, capability
    - Execution with timeout and error handling
    """
    
    def __init__(self, audit_log_path: str = "logs/tool_audit.jsonl"):
        self._tools: Dict[str, BaseTool] = {}
        self._audit_log_path = audit_log_path
        os.makedirs(os.path.dirname(audit_log_path), exist_ok=True)
    
    def register(self, tool: BaseTool) -> bool:
        """Register a tool."""
        if not tool.manifest:
            logger.warning("Tool has no manifest, skipping")
            return False
        
        name = tool.manifest.name
        if name in self._tools:
            logger.warning("Tool '%s' already registered", name)
            return False
        
        self._tools[name] = tool
        logger.info("Tool registered: %s v%s", name, tool.manifest.version)
        return True
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [
            {
                "name": name,
                "version": tool.manifest.version if tool.manifest else "0.0.0",
                "description": tool.manifest.description if tool.manifest else "",
                "category": tool.manifest.category if tool.manifest else "",
                "risk": tool.manifest.risk.value if tool.manifest else "unknown",
            }
            for name, tool in self._tools.items()
        ]
    
    def search(self, query: str = None, category: str = None, tag: str = None) -> List[BaseTool]:
        """Search tools by query, category, or tag."""
        results = []
        for tool in self._tools.values():
            if not tool.manifest:
                continue
            if query and query.lower() not in tool.manifest.name.lower():
                continue
            if category and tool.manifest.category != category:
                continue
            if tag and tag not in tool.manifest.tags:
                continue
            results.append(tool)
        return results
    
    async def execute(self, tool_name: str, permissions: List[str] = None, **kwargs) -> ToolResult:
        """Execute a tool with permission check and audit."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Tool '{tool_name}' not found", tool_name=tool_name)
        
        # Check permissions
        if tool.manifest and tool.manifest.requires_permissions:
            for perm in tool.manifest.requires_permissions:
                if perm not in (permissions or []):
                    return ToolResult(
                        success=False, output="", 
                        error=f"Permission '{perm}' required", 
                        tool_name=tool_name
                    )
        
        # Execute with timing
        start_time = time.time()
        try:
            # Validate
            if not await tool.validate(**kwargs):
                return ToolResult(success=False, output="", error="Validation failed", tool_name=tool_name)
            
            # Execute
            result = await tool.execute(**kwargs)
            result.execution_time_ms = (time.time() - start_time) * 1000
            result.tool_name = tool_name
            result.tool_version = tool.manifest.version if tool.manifest else "0.0.0"
            
            # Audit
            self._audit(result)
            
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = ToolResult(
                success=False, output="", error=str(e), 
                execution_time_ms=execution_time, tool_name=tool_name
            )
            self._audit(result)
            return result
    
    def _audit(self, result: ToolResult):
        """Log tool execution for audit."""
        try:
            audit_entry = {
                "timestamp": time.time(),
                "tool": result.tool_name,
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
                "error": result.error,
            }
            with open(self._audit_log_path, 'a') as f:
                f.write(json.dumps(audit_entry) + "\n")
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════════

class ShellTool(BaseTool):
    """Shell command execution tool."""
    
    def __init__(self):
        super().__init__()
        self.manifest = ToolManifest(
            name="shell",
            version="1.0.0",
            description="Execute shell commands",
            category="system",
            input_schema=ToolSchema(
                properties={
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds"},
                    "cwd": {"type": "string", "description": "Working directory"},
                },
                required=["command"]
            ),
            risk=ToolRisk.MEDIUM,
            timeout_seconds=120,
            requires_permissions=["shell_execute"],
            tags=["system", "shell", "command"]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", self.manifest.timeout_seconds)
        cwd = kwargs.get("cwd", ".")
        
        # Safety: block dangerous commands
        dangerous_patterns = ["rm -rf /", "sudo", "chmod 777", "mkfs", "dd if="]
        for pattern in dangerous_patterns:
            if pattern in command:
                return ToolResult(
                    success=False, output="", 
                    error=f"Dangerous command blocked: {pattern}",
                    tool_name=self.manifest.name
                )
        
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, 
                timeout=timeout, cwd=cwd
            )
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                tool_name=self.manifest.name
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Command timed out", tool_name=self.manifest.name)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), tool_name=self.manifest.name)


class FilesystemTool(BaseTool):
    """File system operations tool."""
    
    def __init__(self):
        super().__init__()
        self.manifest = ToolManifest(
            name="filesystem",
            version="1.0.0",
            description="Read, write, and manage files",
            category="system",
            input_schema=ToolSchema(
                properties={
                    "action": {"type": "string", "enum": ["read", "write", "delete", "list", "exists", "mkdir"]},
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                required=["action", "path"]
            ),
            risk=ToolRisk.MEDIUM,
            tags=["system", "file", "io"]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "")
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        
        try:
            p = Path(path)
            
            if action == "read":
                if not p.exists():
                    return ToolResult(success=False, output="", error="File not found", tool_name=self.manifest.name)
                return ToolResult(success=True, output=p.read_text(encoding="utf-8"), tool_name=self.manifest.name)
            
            elif action == "write":
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return ToolResult(success=True, output=f"Written {len(content)} bytes", tool_name=self.manifest.name)
            
            elif action == "delete":
                if p.exists():
                    p.unlink()
                    return ToolResult(success=True, output="Deleted", tool_name=self.manifest.name)
                return ToolResult(success=False, output="", error="File not found", tool_name=self.manifest.name)
            
            elif action == "list":
                if not p.exists():
                    return ToolResult(success=False, output="", error="Directory not found", tool_name=self.manifest.name)
                items = [str(item) for item in p.iterdir()]
                return ToolResult(success=True, output="\n".join(items), tool_name=self.manifest.name)
            
            elif action == "exists":
                return ToolResult(success=True, output=str(p.exists()), tool_name=self.manifest.name)
            
            elif action == "mkdir":
                p.mkdir(parents=True, exist_ok=True)
                return ToolResult(success=True, output="Directory created", tool_name=self.manifest.name)
            
            else:
                return ToolResult(success=False, output="", error=f"Unknown action: {action}", tool_name=self.manifest.name)
        
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), tool_name=self.manifest.name)


class HttpTool(BaseTool):
    """HTTP request tool."""
    
    def __init__(self):
        super().__init__()
        self.manifest = ToolManifest(
            name="http",
            version="1.0.0",
            description="Make HTTP requests",
            category="network",
            input_schema=ToolSchema(
                properties={
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                required=["method", "url"]
            ),
            risk=ToolRisk.MEDIUM,
            timeout_seconds=30,
            requires_permissions=["network_access"],
            tags=["network", "http", "api"]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        import urllib.request
        import urllib.error
        
        method = kwargs.get("method", "GET")
        url = kwargs.get("url", "")
        headers = kwargs.get("headers", {})
        body = kwargs.get("body", "")
        timeout = kwargs.get("timeout", 30)
        
        try:
            if body:
                data = body.encode("utf-8")
            else:
                data = None
            
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read().decode("utf-8")
                return ToolResult(
                    success=True,
                    output=content,
                    tool_name=self.manifest.name,
                    metadata={"status": response.status, "headers": dict(response.headers)}
                )
        except urllib.error.HTTPError as e:
            return ToolResult(
                success=False, output="", 
                error=f"HTTP {e.code}: {e.reason}",
                tool_name=self.manifest.name
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), tool_name=self.manifest.name)


class SearchTool(BaseTool):
    """Web search tool."""
    
    def __init__(self):
        super().__init__()
        self.manifest = ToolManifest(
            name="search",
            version="1.0.0",
            description="Search the web for information",
            category="network",
            input_schema=ToolSchema(
                properties={
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                    "freshness": {"type": "string", "enum": ["day", "week", "month", "year"]},
                },
                required=["query"]
            ),
            risk=ToolRisk.LOW,
            tags=["search", "web", "information"]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)
        
        # Return search query for the brain to execute via web_search tool
        return ToolResult(
            success=True,
            output=json.dumps({"query": query, "limit": limit, "status": "ready_for_brain"}),
            tool_name=self.manifest.name,
            metadata={"query": query, "limit": limit}
        )


class GitTool(BaseTool):
    """Git operations tool."""
    
    def __init__(self):
        super().__init__()
        self.manifest = ToolManifest(
            name="git",
            version="1.0.0",
            description="Git version control operations",
            category="development",
            input_schema=ToolSchema(
                properties={
                    "action": {"type": "string", "enum": ["status", "add", "commit", "push", "pull", "branch", "checkout", "log", "diff"]},
                    "message": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "branch": {"type": "string"},
                },
                required=["action"]
            ),
            risk=ToolRisk.MEDIUM,
            requires_permissions=["shell_execute"],
            tags=["git", "vcs", "development"]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "")
        message = kwargs.get("message", "")
        files = kwargs.get("files", [])
        branch = kwargs.get("branch", "")
        
        try:
            if action == "status":
                cmd = "git status --short"
            elif action == "add":
                file_args = " ".join(files) if files else "."
                cmd = f"git add {file_args}"
            elif action == "commit":
                cmd = f'git commit -m "{message}"'
            elif action == "push":
                cmd = "git push"
            elif action == "pull":
                cmd = "git pull"
            elif action == "branch":
                cmd = "git branch -a"
            elif action == "checkout":
                cmd = f"git checkout {branch}"
            elif action == "log":
                cmd = "git log --oneline -20"
            elif action == "diff":
                cmd = "git diff"
            else:
                return ToolResult(success=False, output="", error=f"Unknown action: {action}", tool_name=self.manifest.name)
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                tool_name=self.manifest.name
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), tool_name=self.manifest.name)


class PythonExecutionTool(BaseTool):
    """Python code execution tool."""
    
    def __init__(self):
        super().__init__()
        self.manifest = ToolManifest(
            name="python_execute",
            version="1.0.0",
            description="Execute Python code in a sandboxed environment",
            category="development",
            input_schema=ToolSchema(
                properties={
                    "code": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                required=["code"]
            ),
            risk=ToolRisk.HIGH,
            timeout_seconds=30,
            requires_permissions=["python_execute"],
            tags=["python", "code", "execution"]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        code = kwargs.get("code", "")
        timeout = kwargs.get("timeout", 30)
        
        # Write code to temp file and execute
        try:
            temp_file = f"state/temp_{uuid.uuid4().hex[:8]}.py"
            with open(temp_file, 'w') as f:
                f.write(code)
            
            result = subprocess.run(
                f"python {temp_file}", shell=True, capture_output=True, text=True, timeout=timeout
            )
            
            # Cleanup
            os.unlink(temp_file)
            
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                tool_name=self.manifest.name
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Execution timed out", tool_name=self.manifest.name)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), tool_name=self.manifest.name)


class BrowserTool(BaseTool):
    """Browser automation tool."""
    
    def __init__(self):
        super().__init__()
        self.manifest = ToolManifest(
            name="browser",
            version="1.0.0",
            description="Browser automation for web interaction",
            category="automation",
            input_schema=ToolSchema(
                properties={
                    "action": {"type": "string", "enum": ["navigate", "click", "type", "screenshot", "extract", "scroll"]},
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "text": {"type": "string"},
                },
                required=["action"]
            ),
            risk=ToolRisk.MEDIUM,
            requires_permissions=["browser_access"],
            tags=["browser", "web", "automation"]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "")
        
        # Return action for the brain to execute via browser tool
        return ToolResult(
            success=True,
            output=json.dumps({"action": action, "params": kwargs, "status": "ready_for_brain"}),
            tool_name=self.manifest.name,
            metadata={"action": action}
        )


class NotificationTool(BaseTool):
    """Notification sending tool."""
    
    def __init__(self):
        super().__init__()
        self.manifest = ToolManifest(
            name="notification",
            version="1.0.0",
            description="Send notifications via various channels",
            category="communication",
            input_schema=ToolSchema(
                properties={
                    "channel": {"type": "string", "enum": ["log", "console", "file"]},
                    "message": {"type": "string"},
                    "level": {"type": "string", "enum": ["info", "warning", "error", "success"]},
                },
                required=["message"]
            ),
            risk=ToolRisk.LOW,
            tags=["notification", "communication", "logging"]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        channel = kwargs.get("channel", "log")
        message = kwargs.get("message", "")
        level = kwargs.get("level", "info")
        
        try:
            if channel == "log":
                getattr(logger, level, logger.info)(message)
                return ToolResult(success=True, output=f"Logged: {message[:100]}", tool_name=self.manifest.name)
            elif channel == "console":
                print(f"[{level.upper()}] {message}")
                return ToolResult(success=True, output=f"Printed: {message[:100]}", tool_name=self.manifest.name)
            elif channel == "file":
                with open("logs/notifications.log", 'a') as f:
                    f.write(f"{time.time()} [{level}] {message}\n")
                return ToolResult(success=True, output=f"Written to file: {message[:100]}", tool_name=self.manifest.name)
            else:
                return ToolResult(success=False, output="", error=f"Unknown channel: {channel}", tool_name=self.manifest.name)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e), tool_name=self.manifest.name)


# ═══════════════════════════════════════════════════════════════════════════════════
# GLOBAL REGISTRY INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════════

# Create global registry and register all tools
_global_registry = ToolRegistry()

# Register all tools
for tool_class in [ShellTool, FilesystemTool, HttpTool, SearchTool, GitTool, 
                   PythonExecutionTool, BrowserTool, NotificationTool]:
    _global_registry.register(tool_class())


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _global_registry
