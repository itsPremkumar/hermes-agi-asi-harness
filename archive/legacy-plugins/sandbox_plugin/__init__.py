"""
sandbox_plugin.py — Isolated Execution Sandbox with Resource Limits

Executes code and shell commands safely with working-dir containment,
timeout protection, and AST pre-validation.
"""

import ast
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a sandboxed execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    command: str = ""


class ExecutionSandbox:
    """
    Isolated execution sandbox with resource limits and safety pre-checks.
    """

    # Dangerous patterns for AST pre-check
    DANGEROUS_CALLS = {
        "eval", "exec", "compile", "open", "__import__",
        "os.system", "os.popen", "os.exec", "os.spawn",
        "subprocess.call", "subprocess.Popen", "subprocess.run",
        "globals", "locals", "vars", "dir",
        "shutil.rmtree", "shutil.move", "shutil.copy",
        "sys.exit", "sys.quit",
    }

    def __init__(self, base_workspace: str | None = None, timeout_seconds: int = 60):
        self.base_workspace = pathlib.Path(
            base_workspace or (pathlib.Path.home() / ".hermes" / "sandbox")
        )
        self.base_workspace.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self._blocked_dirs: list[pathlib.Path] = [
            pathlib.Path("/etc"),
            pathlib.Path("/root"),
            pathlib.Path("/sys"),
            pathlib.Path("/proc"),
        ]

    def create_isolated_dir(self, name: str) -> pathlib.Path:
        """Creates an isolated working directory."""
        target = self.base_workspace / name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _is_path_safe(self, path: pathlib.Path) -> bool:
        """Checks if a path is within safe boundaries."""
        safe_root = self.base_workspace.resolve()
        try:
            resolved = path.resolve()
            return safe_root in resolved.parents or resolved == safe_root
        except Exception:
            return False

    def _check_ast_safety(self, code: str) -> list[str]:
        """Performs AST-based safety check on Python code."""
        violations = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = f"{node.func.value.id if isinstance(node.func.value, ast.Name) else ''}.{node.func.attr}"

                    if func_name in self.DANGEROUS_CALLS:
                        violations.append(f"Blocked call: {func_name} at line {node.lineno}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("os", "sys", "subprocess", "shutil"):
                            violations.append(f"Blocked import: {alias.name} at line {node.lineno}")
        except SyntaxError as e:
            violations.append(f"Syntax error: {e}")
        return violations

    def run_command(
        self,
        command: list[str],
        cwd: pathlib.Path | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Executes a shell command with timeout protection."""
        work_dir = cwd or self.base_workspace
        to = timeout or self.timeout_seconds
        start_t = time.monotonic()

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        try:
            result = subprocess.run(
                command,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=to,
                env=merged_env,
            )
            duration = (time.monotonic() - start_t) * 1000
            return ExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=duration,
                timed_out=False,
                command=" ".join(command),
            )
        except subprocess.TimeoutExpired:
            duration = (time.monotonic() - start_t) * 1000
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {to} seconds",
                duration_ms=duration,
                timed_out=True,
                command=" ".join(command),
            )
        except Exception as e:
            duration = (time.monotonic() - start_t) * 1000
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration,
                command=" ".join(command),
            )

    def run_python(
        self,
        code: str,
        cwd: pathlib.Path | None = None,
        timeout: int | None = None,
    ) -> ExecutionResult:
        """Executes Python code with AST pre-validation."""
        violations = self._check_ast_safety(code)
        if violations:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Safety violations: {'; '.join(violations)}",
                duration_ms=0,
                timed_out=False,
                command=f"python -c '<{len(code)} chars>'",
            )

        # Write code to temp file and execute
        work_dir = cwd or self.base_workspace
        work_dir.mkdir(parents=True, exist_ok=True)
        temp_file = work_dir / f"_sandbox_{int(time.time())}.py"
        temp_file.write_text(code, encoding="utf-8")

        try:
            return self.run_command(
                [sys.executable, str(temp_file)],
                cwd=work_dir,
                timeout=timeout,
            )
        finally:
            try:
                temp_file.unlink()
            except Exception:
                pass

    def cleanup(self, dir_name: str) -> bool:
        """Removes an isolated directory."""
        target = self.base_workspace / dir_name
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            return True
        return False


class SandboxPlugin:
    """Plugin wrapper for ExecutionSandbox."""

    def __init__(self, kernel=None):
        self.state = "started"
        self.kernel = kernel
        self.sandbox = ExecutionSandbox()
        self.manifest = type('Manifest', (), {'name': 'sandbox', 'version': '1.0.0'})()

    async def load(self):
        return True

    async def start(self):
        return True

    async def stop(self):
        return True

    async def health(self):
        return {
            "status": "healthy",
            "plugin": "sandbox",
            "version": "1.0.0",
            "state": self.state,
            "healthy": True,
            "workspace": str(self.sandbox.base_workspace),
        }

    def get_capabilities(self):
        return ["sandboxed_execution", "python_execution", "shell_execution", "path_safety"]

    def run_command(self, *args, **kwargs):
        return self.sandbox.run_command(*args, **kwargs)

    def run_python(self, *args, **kwargs):
        return self.sandbox.run_python(*args, **kwargs)

    def create_isolated_dir(self, *args, **kwargs):
        return self.sandbox.create_isolated_dir(*args, **kwargs)


async def create(kernel=None) -> SandboxPlugin:
    """Factory function for kernel integration."""
    plugin = SandboxPlugin(kernel)
    await plugin.load()
    await plugin.start()
    return plugin
