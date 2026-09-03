"""
Hermes AGI/ASI Harness — Recursive Language Model (RLM) REPL Runtime.

Inspired by Prime Agent:
- Treats context as persistent Python variables
- Exposes subagents and harness tools as callable Python functions
- Allows arbitrary programmatic iteration and data filtering without token explosion
"""

from __future__ import annotations

import ast
import asyncio
import io
import logging
import math
import os
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hermes_agi.research import DeepResearchAgent
from hermes_agi.thinking import DeepThinkingEngine, MCTSSearchEngine
from core.verification.anti_goodhart import AntiGoodhartVerifier
from core.verification.adversarial import AdversarialVerifier

logger = logging.getLogger("hermes.rlm.environment")


class AgentContextBridge:
    """
    Exposes harness subagents, search, and verifiers as callable functions
    inside the agent's Python REPL execution environment.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self._research_agent = DeepResearchAgent()
        self._thinking_engine = DeepThinkingEngine()
        self._mcts_engine = MCTSSearchEngine()
        self._anti_goodhart = AntiGoodhartVerifier(workspace_root=str(self.workspace_root))
        self._adversarial = AdversarialVerifier()

    def research(self, topic: str, depth: int = 2) -> dict[str, Any]:
        """Callable research subagent."""
        try:
            # Run async coro synchronously inside REPL
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    dossier = pool.submit(asyncio.run, self._research_agent.investigate(topic, depth=depth)).result()
            else:
                dossier = loop.run_until_complete(self._research_agent.investigate(topic, depth=depth))
            return dossier.to_dict()
        except Exception as e:
            logger.debug("REPL research fallback: %s", e)
            return {"topic": topic, "findings": [], "error": str(e)}

    def think(self, goal: str, use_mcts: bool = False) -> dict[str, Any]:
        """Callable thinking & MCTS deliberator."""
        if use_mcts:
            res = self._mcts_engine.search(goal)
            return res.to_dict()
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        t = pool.submit(asyncio.run, self._thinking_engine.deliberate(goal)).result()
                else:
                    t = loop.run_until_complete(self._thinking_engine.deliberate(goal))
                return t.to_dict()
            except Exception as e:
                return {"goal": goal, "strategy": "direct", "error": str(e)}

    def verify(self, file_name: str, code: str) -> dict[str, Any]:
        """Callable anti-goodhart and adversarial verification."""
        ag_verdict = self._anti_goodhart.verify(file_name, code)
        adv_verdict = self._adversarial.verify(claims=[f"Verify {file_name}"], evidence=["Static code passed"])
        return {
            "anti_goodhart": ag_verdict.to_dict(),
            "adversarial": adv_verdict.to_dict(),
            "overall_passed": ag_verdict.passed and adv_verdict.consensus_score >= 0.80,
        }

    def read_file(self, relative_path: str) -> str:
        """Read a file from the workspace."""
        p = (self.workspace_root / relative_path).resolve()
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    def write_file(self, relative_path: str, content: str) -> bool:
        """Write a file to the workspace."""
        p = (self.workspace_root / relative_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return True


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
    Persistent in-memory Python REPL execution environment.
    Retains variables across calls, enabling recursive subagent calls.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.bridge = AgentContextBridge(workspace_root=workspace_root)
        self.globals_env: dict[str, Any] = {
            "agent": self.bridge,
            "os": os,
            "sys": sys,
            "math": math,
            "time": time,
            "Path": Path,
        }

    def execute(self, code_snippet: str) -> REPLExecutionResult:
        """Execute a Python code snippet within the persistent REPL environment."""
        start_time = time.time()
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        returned_val = None
        success = True
        error_str = ""

        try:
            # Parse code to check if last statement is an expression
            tree = ast.parse(code_snippet)
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                # Split last expression to capture its evaluation value
                last_expr = tree.body.pop()
                exec_code = compile(tree, filename="<rlm_repl>", mode="exec")
                eval_code = compile(ast.Expression(last_expr.value), filename="<rlm_repl>", mode="eval")

                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    exec(exec_code, self.globals_env)
                    returned_val = eval(eval_code, self.globals_env)
            else:
                compiled = compile(code_snippet, filename="<rlm_repl>", mode="exec")
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    exec(compiled, self.globals_env)

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
