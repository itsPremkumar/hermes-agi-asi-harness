"""
Hermes AGI/ASI Harness — Recursive Language Model (RLM) REPL Runtime.

Ported & Enhanced from Prime Agent (prime-agent-runtime/src/rlm/repl.py):
- Persistent CPython execution with top-level `await` (PyCF_ALLOW_TOP_LEVEL_AWAIT)
- Dedicated persistent asyncio event loop running on a background worker thread
- Exposes `rlm` (RLMBridge) with recursive subagents (`await rlm.run()`)
- In-memory Python heap snapshots and restorations
"""

from __future__ import annotations

import ast
import asyncio
import io
import inspect
import linecache
import logging
import math
import os
import sys
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .bridge import RLMBridge, RLMSpawnHandle

logger = logging.getLogger("hermes.rlm.environment")


@dataclass
class REPLExecutionResult:
    """Output from an RLM REPL evaluation step."""
    code: str
    stdout: str
    stderr: str
    returned_value: Any
    success: bool
    duration_seconds: float
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returned_value": str(self.returned_value) if self.returned_value is not None else None,
            "success": self.success,
            "duration_seconds": round(self.duration_seconds, 3),
            "error": self.error,
        }


class RLMREPLExecutor:
    """
    Persistent in-memory Python REPL execution environment with top-level await.
    Runs on a persistent background asyncio loop, enabling native `await rlm.run()`.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.bridge = RLMBridge(workspace_root=str(self.workspace_root))

        # Start persistent background asyncio event loop
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._loop_thread.start()

        self._cell_counter = 0

        # Persistent REPL globals
        self.globals_env: dict[str, Any] = {
            "rlm": self.bridge,
            "agent": self.bridge,
            "asyncio": asyncio,
            "os": os,
            "sys": sys,
            "math": math,
            "time": time,
            "Path": Path,
            "_": None,
        }

    def _run_event_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def execute(self, code_snippet: str) -> REPLExecutionResult:
        """
        Execute a Python code snippet with top-level await in the persistent environment.
        Dispatches to the background loop thread and waits synchronously for completion.
        """
        future = asyncio.run_coroutine_threadsafe(self._execute_async(code_snippet), self._loop)
        try:
            return future.result(timeout=60)
        except Exception as e:
            return REPLExecutionResult(
                code=code_snippet,
                stdout="",
                stderr=str(e),
                returned_value=None,
                success=False,
                duration_seconds=0.0,
                error=f"{type(e).__name__}: {e}",
            )

    async def _execute_async(self, code_snippet: str) -> REPLExecutionResult:
        """Internal asynchronous cell executor with top-level await compilation."""
        self._cell_counter += 1
        cell_name = f"<cell-{self._cell_counter}>"
        linecache.cache[cell_name] = (len(code_snippet), None, code_snippet.splitlines(keepends=True), cell_name)

        start_time = time.time()
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        returned_val = None
        success = True
        error_str = ""

        try:
            # Parse AST to check trailing expression
            tree = ast.parse(code_snippet, filename=cell_name)
            last_expr = None
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                last_expr = tree.body.pop()

            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                # 1. Execute body statements with top-level await enabled
                if tree.body:
                    co_exec = compile(
                        tree,
                        filename=cell_name,
                        mode="exec",
                        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                    )
                    res_exec = eval(co_exec, self.globals_env)
                    if inspect.iscoroutine(res_exec):
                        await res_exec

                # 2. Evaluate trailing expression if present
                if last_expr is not None:
                    expr_ast = ast.Expression(last_expr.value)
                    co_eval = compile(
                        expr_ast,
                        filename=cell_name,
                        mode="eval",
                        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                    )
                    res_eval = eval(co_eval, self.globals_env)
                    if inspect.iscoroutine(res_eval):
                        returned_val = await res_eval
                    else:
                        returned_val = res_eval

                    self.globals_env["_"] = returned_val

        except Exception as e:
            success = False
            error_str = f"{type(e).__name__}: {e}"
            stderr_buf.write(error_str)

        return REPLExecutionResult(
            code=code_snippet,
            stdout=stdout_buf.getvalue(),
            stderr=stderr_buf.getvalue(),
            returned_value=returned_val,
            success=success,
            duration_seconds=time.time() - start_time,
            error=error_str,
        )

    def get_variable(self, name: str) -> Any:
        return self.globals_env.get(name)

    def set_variable(self, name: str, val: Any) -> None:
        self.globals_env[name] = val

    def snapshot_memory(self, snapshot_name: str) -> str:
        """Snapshot current REPL variables to disk."""
        return self.bridge.snapshot(snapshot_name, self.globals_env)

    def restore_memory(self, snapshot_name: str) -> bool:
        """Restore variables from a disk snapshot into REPL globals."""
        loaded = self.bridge.restore(snapshot_name)
        if loaded:
            self.globals_env.update(loaded)
            return True
        return False

    def close(self) -> None:
        """Stop background event loop cleanly."""
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
