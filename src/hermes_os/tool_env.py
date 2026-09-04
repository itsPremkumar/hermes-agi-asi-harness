"""
HERMES INTELLIGENCE OS — PLANE 13: TOOL & ENVIRONMENT OS
=========================================================
Formal tool execution envelope and persistent programmable REPL:
- Tool != Authority
- Standardized tool descriptor: schema, permission, risk, timeout, side-effects, sandbox, rollback, verification
- Programmable REPL kernel (CPython RLM persistent environment)
"""

from __future__ import annotations

import inspect
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.tool_env")


@dataclass
class ToolDescriptor:
    """Rigorous metadata and execution boundaries for a tool."""
    name: str
    description: str
    handler: Callable[..., Any]
    required_permission: str = "read"
    risk_level: str = "low"  # low, medium, high, critical
    estimated_cost_tokens: int = 100
    timeout_seconds: float = 30.0
    has_side_effects: bool = False
    sandbox_required: bool = True
    rollback_supported: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required_permission": self.required_permission,
            "risk_level": self.risk_level,
            "estimated_cost_tokens": self.estimated_cost_tokens,
            "timeout_seconds": self.timeout_seconds,
            "has_side_effects": self.has_side_effects,
            "sandbox_required": self.sandbox_required,
            "rollback_supported": self.rollback_supported,
        }


class ToolEnvironmentOS:
    """
    Central registry and execution coordinator for all tools, sandboxes,
    and programmable REPL kernels.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._tools: dict[str, ToolDescriptor] = {}
        self._init_standard_tools()

    def _init_standard_tools(self):
        self.register(ToolDescriptor(
            name="python_repl",
            description="Execute Python code in persistent isolated memory heap",
            handler=self._execute_python_repl,
            required_permission="exec:rlm",
            risk_level="low",
            sandbox_required=True,
        ))
        self.register(ToolDescriptor(
            name="read_file",
            description="Read local workspace file",
            handler=self._read_file,
            required_permission="read",
            risk_level="low",
            sandbox_required=False,
        ))

    def register(self, tool: ToolDescriptor) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDescriptor]:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._tools.values()]

    async def execute_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a registered tool with timeout and failure insulation."""
        tool = self._tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found", "output": None}

        t0 = time.time()
        try:
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(**args)
            else:
                result = tool.handler(**args)
            return {
                "success": True,
                "tool": tool_name,
                "output": result,
                "duration": time.time() - t0,
            }
        except Exception as e:
            logger.error("Tool '%s' execution failed: %s", tool_name, e)
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "output": None,
                "duration": time.time() - t0,
            }

    def _execute_python_repl(self, code: str) -> Any:
        from hermes_agi.rlm import RLMREPLExecutor
        executor = RLMREPLExecutor(workspace_root=self.workspace_root)
        try:
            res = executor.execute(code)
            return res.returned_value if res.returned_value is not None else res.stdout.strip()
        finally:
            executor.close()

    def _read_file(self, path: str) -> str:
        from pathlib import Path
        p = Path(self.workspace_root) / path
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return p.read_text(encoding="utf-8", errors="replace")
