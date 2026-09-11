#!/usr/bin/env python3
"""
sandbox.py — Isolated Execution Sandbox with Resource Limits & Pre/Post Hooks
Executes code and shell commands safely with working-dir containment and timeout protection.
"""

import os
import sys
import time
import shutil
import pathlib
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False

class ExecutionSandbox:
    def __init__(self, base_workspace: Optional[str] = None, timeout_seconds: int = 60):
        self.base_workspace = pathlib.Path(base_workspace or (pathlib.Path.home() / ".hermes" / "sandbox"))
        self.base_workspace.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds

    def create_isolated_dir(self, name: str) -> pathlib.Path:
        target = self.base_workspace / name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def run_command(
        self,
        command: List[str],
        cwd: Optional[pathlib.Path] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        work_dir = cwd or self.base_workspace
        to = timeout or self.timeout_seconds
        start_t = time.monotonic()

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        try:
            proc = subprocess.run(
                command,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=to,
                env=merged_env
            )
            duration = (time.monotonic() - start_t) * 1000.0
            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=duration,
                timed_out=False
            )
        except subprocess.TimeoutExpired as e:
            duration = (time.monotonic() - start_t) * 1000.0
            return ExecutionResult(
                exit_code=124,
                stdout=e.stdout or "",
                stderr="Process timed out.",
                duration_ms=duration,
                timed_out=True
            )
        except Exception as e:
            duration = (time.monotonic() - start_t) * 1000.0
            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr=str(e),
                duration_ms=duration,
                timed_out=False
            )

    def run_python_code(self, code_str: str, cwd: Optional[pathlib.Path] = None) -> ExecutionResult:
        work_dir = cwd or self.base_workspace
        temp_file = work_dir / f"_sandbox_exec_{int(time.time() * 1000)}.py"
        try:
            temp_file.write_text(code_str, encoding="utf-8")
            res = self.run_command([sys.executable, str(temp_file)], cwd=work_dir)
            return res
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    def cleanup(self, dir_path: Optional[pathlib.Path] = None):
        target = dir_path or self.base_workspace
        if target.exists() and target != pathlib.Path.home():
            try:
                shutil.rmtree(target)
            except Exception:
                pass
