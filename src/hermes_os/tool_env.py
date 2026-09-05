"""
HERMES INTELLIGENCE OS — PLANE 13: TOOL & ENVIRONMENT OS
=========================================================
Formal tool execution envelope and persistent programmable REPL:
- Tool != Authority
- Standardized tool descriptor: schema, permission, risk, timeout, side-effects, sandbox, rollback, verification
- Programmable REPL kernel (CPython RLM persistent environment)
"""

from __future__ import annotations

import asyncio
import fnmatch
import inspect
import logging
import os
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .safety_kernel import SafetyKernel, SafetyVerdict

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
    parameters_schema: dict[str, Any] = field(default_factory=dict)

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
            "parameters_schema": self.parameters_schema,
        }


class ToolEnvironmentOS:
    """
    Central registry and execution coordinator for all tools, sandboxes,
    developer agency tools, and programmable REPL kernels.
    """

    def __init__(self, workspace_root: str = ".", safety_kernel: Optional[SafetyKernel] = None):
        self.workspace_root = workspace_root
        self.safety_kernel = safety_kernel or SafetyKernel()
        self._tools: dict[str, ToolDescriptor] = {}
        self._metrics = None
        self._init_standard_tools()

    def _metrics_collector(self) -> Any:
        if self._metrics is None:
            try:
                from .plane_metrics import MetricsCollector
                self._metrics = MetricsCollector.for_workspace(self.workspace_root)
            except Exception:
                self._metrics = False
        return self._metrics or None

    def _record_metric(self, tool_name: str, ok: bool, duration: float, tokens: int = 100) -> None:
        try:
            mc = self._metrics_collector()
            if mc is None:
                return
            mc.record_plane(query_id=f"tool-{tool_name}", plane_name=tool_name,
                            tokens_used=tokens, cost=tokens * 0.003 / 1000,
                            latency_ms=duration * 1000.0, error=not ok)
        except Exception:
            pass

    def _init_standard_tools(self):
        # 1. REPL & Read
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
        # 2. File Modification Tools
        self.register(ToolDescriptor(
            name="write_file",
            description="Write or overwrite a file in the workspace",
            handler=self._write_file,
            required_permission="write",
            risk_level="medium",
            has_side_effects=True,
        ))
        self.register(ToolDescriptor(
            name="edit_file",
            description="Surgically replace target content in an existing file",
            handler=self._edit_file,
            required_permission="write",
            risk_level="medium",
            has_side_effects=True,
            rollback_supported=True,
        ))
        # 3. Filesystem Exploration & Search Tools
        self.register(ToolDescriptor(
            name="list_dir",
            description="List directory contents with file metadata",
            handler=self._list_dir,
            required_permission="read",
            risk_level="low",
        ))
        self.register(ToolDescriptor(
            name="grep_search",
            description="Ripgrep-style pattern matching across files",
            handler=self._grep_search,
            required_permission="read",
            risk_level="low",
        ))
        self.register(ToolDescriptor(
            name="find_by_name",
            description="Find files matching a glob pattern",
            handler=self._find_by_name,
            required_permission="read",
            risk_level="low",
        ))
        # 4. Sandboxed Shell Execution
        self.register(ToolDescriptor(
            name="execute_shell",
            description="Execute shell command safely under SafetyKernel policy",
            handler=self._execute_shell,
            required_permission="exec:shell",
            risk_level="high",
            has_side_effects=True,
        ))
        # 5. Version Control & Patching Tools
        self.register(ToolDescriptor(
            name="git_status",
            description="Get workspace git status",
            handler=self._git_status,
            required_permission="read",
            risk_level="low",
        ))
        self.register(ToolDescriptor(
            name="git_diff",
            description="Get workspace git diff",
            handler=self._git_diff,
            required_permission="read",
            risk_level="low",
        ))
        self.register(ToolDescriptor(
            name="apply_patch",
            description="Apply a unified git diff patch to the workspace",
            handler=self._apply_patch,
            required_permission="write",
            risk_level="high",
            has_side_effects=True,
            rollback_supported=True,
        ))
        self.register(ToolDescriptor(
            name="compact_context",
            description="Extractively compact oversized text; full copy archived under .hermes/context_archive",
            handler=self._compact_context,
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

    async def execute_tool(self, tool_name: str, args: dict[str, Any],
                           goal_contract: Optional[Any] = None,
                           caller_identity: str = "agent:worker") -> dict[str, Any]:
        """Execute a registered tool behind SafetyKernel + timeout + failure insulation."""
        tool = self._tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found", "output": None}

        # 1. Universal safety gate (all tools, not just shell)
        try:
            verdict, reason, risk = self.safety_kernel.evaluate_action(
                action_type=tool_name,
                action_args=dict(args or {}),
                goal_contract=goal_contract,
                caller_identity=caller_identity,
            )
            if verdict == SafetyVerdict.BLOCK:
                logger.warning("Tool '%s' blocked by SafetyKernel: %s", tool_name, reason)
                return {"success": False, "tool": tool_name, "error": f"Blocked: {reason}",
                        "output": None, "result": None, "verdict": "block", "risk": risk}
            escalated = verdict == SafetyVerdict.ESCALATE
        except Exception as e:
            logger.debug("Safety gate error (fail-open to handler): %s", e)
            escalated = False
            risk = 0.1

        # 2. Timeout-guarded execution (threads for sync handlers so event loop never blocks)
        t0 = time.time()
        try:
            if inspect.iscoroutinefunction(tool.handler):
                result = await asyncio.wait_for(tool.handler(**args), timeout=tool.timeout_seconds)
            else:
                import concurrent.futures as _cf
                loop = asyncio.get_running_loop()
                with _cf.ThreadPoolExecutor(max_workers=1) as pool:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(pool, lambda: tool.handler(**args)),
                        timeout=tool.timeout_seconds,
                    )
            duration = time.time() - t0
            out: dict[str, Any] = {
                "success": True,
                "tool": tool_name,
                "output": result,
                "result": result,
                "duration": duration,
                "verdict": "escalated" if escalated else "allow",
            }
            self._record_metric(tool_name, True, duration, getattr(tool, "estimated_cost_tokens", 100))
            try:
                from .tool_scoring import ToolScorecard
                ToolScorecard(workspace_root=self.workspace_root).record(
                    tool_name, True, latency_s=time.time() - t0,
                    tokens=getattr(tool, "estimated_cost_tokens", 100),
                    risk=getattr(tool, "risk_level", "low"),
                    verdict=out["verdict"])
            except Exception:
                pass
            # 3. OUTPUT LAW metadata for mutating tools: capture git diff stat
            if tool.has_side_effects and tool_name in ("write_file", "edit_file", "apply_patch", "execute_shell"):
                try:
                    out["output_law"] = self.output_law_report()
                except Exception:
                    pass
            return out
        except asyncio.TimeoutError:
            logger.error("Tool '%s' timed out after %.1fs", tool_name, tool.timeout_seconds)
            return {"success": False, "tool": tool_name, "error": "timeout", "output": None,
                    "result": None, "duration": time.time() - t0}
        except Exception as e:
            logger.error("Tool '%s' execution failed: %s", tool_name, e)
            duration = time.time() - t0
            try:
                from .tool_scoring import ToolScorecard
                ToolScorecard(workspace_root=self.workspace_root).record(
                    tool_name, False, latency_s=duration,
                    tokens=getattr(tool, "estimated_cost_tokens", 100),
                    risk=getattr(tool, "risk_level", "low"), verdict="error")
            except Exception:
                pass
            self._record_metric(tool_name, False, duration, getattr(tool, "estimated_cost_tokens", 100))
            return {"success": False, "tool": tool_name, "error": str(e), "output": None,
                    "result": None, "duration": duration}

    def output_law_report(self) -> dict[str, Any]:
        """AGX-style OUTPUT LAW: every mutation must yield an observable diff or artifact."""
        try:
            st = subprocess.run(["git", "status", "--short"], cwd=self.workspace_root,
                                capture_output=True, text=True, timeout=10)
            df = subprocess.run(["git", "diff", "--stat"], cwd=self.workspace_root,
                                capture_output=True, text=True, timeout=10)
            status = (st.stdout or "").strip()
            stat = (df.stdout or "").strip()
            return {"has_diff": bool(status or stat), "status_short": status[:2000], "diff_stat": stat[:2000]}
        except Exception as e:
            return {"has_diff": False, "error": str(e)}

    def verify_output_law(self, require_diff: bool = True) -> tuple[bool, str]:
        """Returns (ok, reason). No-op mutations fail when require_diff=True."""
        rep = self.output_law_report()
        if require_diff and not rep.get("has_diff"):
            return False, "OUTPUT LAW violation: mutation produced no observable diff/artifact"
        return True, "OUTPUT LAW satisfied"

    def _execute_python_repl(self, code: str) -> Any:
        from hermes_agi.rlm import RLMREPLExecutor
        executor = RLMREPLExecutor(workspace_root=self.workspace_root)
        try:
            res = executor.execute(code)
            return res.returned_value if res.returned_value is not None else res.stdout.strip()
        finally:
            executor.close()

    def _read_file(self, path: str) -> str:
        p = Path(self.workspace_root) / path
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return p.read_text(encoding="utf-8", errors="replace")

    def _write_file(self, path: str, content: str, overwrite: bool = True) -> str:
        p = Path(self.workspace_root) / path
        if p.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {path}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} bytes to {path}"

    def _edit_file(
        self,
        path: str,
        target_content: Optional[str] = None,
        replacement_content: Optional[str] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
    ) -> str:
        target = target_content if target_content is not None else old_str
        replacement = replacement_content if replacement_content is not None else new_str
        if target is None or replacement is None:
            raise ValueError("Either (target_content, replacement_content) or (old_str, new_str) must be provided")
        p = Path(self.workspace_root) / path
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        text = p.read_text(encoding="utf-8")
        if target not in text:
            raise ValueError(f"Target content not found in {path}")
        new_text = text.replace(target, replacement, 1)
        p.write_text(new_text, encoding="utf-8")
        return f"Successfully edited {path}"

    def _list_dir(self, path: str = ".", recursive: bool = False, max_depth: int = 2) -> list[dict[str, Any]]:
        target_dir = Path(self.workspace_root) / path
        if not target_dir.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        results: list[dict[str, Any]] = []
        if recursive:
            for root, dirs, files in os.walk(target_dir):
                if ".git" in root or "__pycache__" in root:
                    continue
                rel = Path(root).relative_to(target_dir)
                if len(rel.parts) > max_depth:
                    continue
                for f in files:
                    fp = Path(root) / f
                    results.append({"name": f, "path": str(fp.relative_to(self.workspace_root)), "type": "file", "size": fp.stat().st_size})
                for d in dirs:
                    dp = Path(root) / d
                    results.append({"name": d, "path": str(dp.relative_to(self.workspace_root)), "type": "directory"})
        else:
            for item in target_dir.iterdir():
                if item.name.startswith(".git"):
                    continue
                results.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.workspace_root)),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                })
        return results

    def _grep_search(self, query: str, path: str = ".", is_regex: bool = False, case_sensitive: bool = True) -> list[dict[str, Any]]:
        target_dir = Path(self.workspace_root) / path
        flags = 0 if case_sensitive else re.IGNORECASE
        pat = re.compile(query if is_regex else re.escape(query), flags)
        matches: list[dict[str, Any]] = []
        for root, _, files in os.walk(target_dir):
            if ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                fp = Path(root) / f
                try:
                    text = fp.read_text(encoding="utf-8", errors="ignore")
                    for line_num, line in enumerate(text.splitlines(), start=1):
                        if pat.search(line):
                            matches.append({
                                "file": str(fp.relative_to(self.workspace_root)),
                                "line_number": line_num,
                                "line": line.strip()[:200],
                            })
                            if len(matches) >= 50:
                                return matches
                except Exception:
                    continue
        return matches

    def _find_by_name(self, pattern: str, path: str = ".") -> list[str]:
        target_dir = Path(self.workspace_root) / path
        found: list[str] = []
        for root, _, files in os.walk(target_dir):
            if ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                if fnmatch.fnmatch(f, pattern):
                    found.append(str((Path(root) / f).relative_to(self.workspace_root)))
                    if len(found) >= 50:
                        return found
        return found

    def _execute_shell(self, command: str, timeout: float = 30.0, cwd: Optional[str] = None) -> dict[str, Any]:
        verdict, reason, risk = self.safety_kernel.evaluate_action(
            action_type="execute_shell",
            action_args={"command": command},
        )
        if verdict == SafetyVerdict.BLOCK:
            raise PermissionError(f"SafetyKernel blocked command execution: {reason} (risk: {risk})")

        run_dir = Path(self.workspace_root) / (cwd or ".")
        proc = subprocess.run(
            command,
            cwd=str(run_dir),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "command": command,
        }

    def _git_status(self) -> str:
        proc = subprocess.run(["git", "status", "--short"], cwd=self.workspace_root, capture_output=True, text=True)
        return proc.stdout.strip()

    def _git_diff(self) -> str:
        proc = subprocess.run(["git", "diff"], cwd=self.workspace_root, capture_output=True, text=True)
        return proc.stdout.strip()

    def _compact_context(self, text: str = "", path: str = "", max_chars: int = 12000) -> dict[str, Any]:
        from .context_compaction import ContextCompactor
        if path and not text:
            text = (Path(self.workspace_root) / path).read_text(encoding="utf-8", errors="replace")
        rep = ContextCompactor(workspace_root=self.workspace_root, max_chars=max_chars).compact(text)
        return {k: (v if k != "compacted" else v[:4000]) for k, v in rep.items()}

    def _apply_patch(self, patch_str: str) -> str:
        proc = subprocess.run(
            ["git", "apply", "-"],
            input=patch_str,
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git apply failed: {proc.stderr}")
        return "Patch applied successfully"

    def durable_mcp(self, mcp_client: Any, lease_seconds: float = 300.0) -> Any:
        """Background lease/poll/cancel executor for long MCP calls."""
        from .mcp_tasks import DurableMCPTasks
        return DurableMCPTasks(mcp_client, lease_seconds=lease_seconds)

    def connect_mcp_client(self, mcp_client: Any, server_name: str, capability_registry: Optional[Any] = None) -> list[str]:
        """
        Dynamically discover and register tools exposed by an MCP client server into ToolEnvironmentOS,
        and optionally propagate them into CapabilityRegistry.
        """
        tools = mcp_client.list_tools(server_name)
        registered_names: list[str] = []
        for tool_spec in tools:
            t_name = tool_spec.get("name")
            if not t_name:
                continue
            qualified_name = f"mcp_{server_name}_{t_name}"

            def make_handler(srv: str, t_orig: str):
                def _handler(**kwargs: Any) -> Any:
                    return mcp_client.call_tool(srv, t_orig, kwargs)
                return _handler

            descriptor = ToolDescriptor(
                name=qualified_name,
                description=tool_spec.get("description", f"Dynamic MCP tool from {server_name}"),
                handler=make_handler(server_name, t_name),
                parameters_schema=tool_spec.get("input_schema", {}),
                required_permission="exec:mcp",
                risk_level=tool_spec.get("risk", "medium"),
                has_side_effects=tool_spec.get("side_effects", True),
            )
            self.register(descriptor)
            registered_names.append(qualified_name)

        if capability_registry is not None and hasattr(capability_registry, "register_mcp_tools"):
            capability_registry.register_mcp_tools(tools, server_name=server_name)

        return registered_names

