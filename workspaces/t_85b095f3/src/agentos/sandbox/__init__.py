"""Sandboxed execution environment for agents."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class SandboxConfig:
    """Configuration for sandboxed execution."""
    max_cpu_time: float = 30.0  # seconds
    max_memory_mb: int = 512
    max_file_size_mb: int = 100
    max_processes: int = 1
    allow_network: bool = False
    allow_write: bool = True
    working_dir: str | None = None
    env_vars: dict[str, str] | None = None


@dataclass
class SandboxResult:
    """Result of sandboxed execution."""
    returncode: int
    stdout: str
    stderr: str
    duration: float
    memory_used_mb: int
    timed_out: bool = False
    killed: bool = False


def _make_preexec(config: SandboxConfig) -> Callable[[], None] | None:
    """Create a preexec function for Unix resource limits, or None on Windows."""
    if platform.system() == "Windows":
        return None

    import resource

    def preexec() -> None:
        # CPU time limit (soft, hard)
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (int(config.max_cpu_time), int(config.max_cpu_time) + 5)
        )
        # Memory limit
        mem_bytes = config.max_memory_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except ValueError:
            pass
        # Process limit
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (config.max_processes, config.max_processes)
        )
        # File size limit
        file_bytes = config.max_file_size_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))

    return preexec


class Sandbox:
    """Sandboxed execution environment using OS-level isolation."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()

    def run(self, command: list[str], input_data: str | None = None) -> SandboxResult:
        """Execute a command in the sandbox."""
        import time

        workdir = self.config.working_dir or tempfile.mkdtemp(prefix="agentos_sandbox_")

        preexec_fn = _make_preexec(self.config)

        env = os.environ.copy()
        if self.config.env_vars:
            env.update(self.config.env_vars)
        if not self.config.allow_network:
            # Disable network by removing proxy vars
            for key in list(env.keys()):
                if "proxy" in key.lower():
                    del env[key]

        start = time.monotonic()
        timed_out = False
        killed = False

        try:
            # Build kwargs - only include preexec_fn on Unix
            kwargs: dict[str, Any] = dict(
                capture_output=True,
                text=True,
                timeout=self.config.max_cpu_time + 5,
                cwd=workdir,
                env=env,
                input=input_data,
            )
            if preexec_fn is not None:
                kwargs["preexec_fn"] = preexec_fn

            proc = subprocess.run(command, **kwargs)
            duration = time.monotonic() - start
            returncode = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            returncode = -1
            timed_out = True
            stdout = ""
            stderr = "Timed out"
        except MemoryError:
            duration = time.monotonic() - start
            returncode = -1
            killed = True
            stdout = ""
            stderr = "Killed (OOM)"

        return SandboxResult(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            memory_used_mb=0,
            timed_out=timed_out,
            killed=killed,
        )

    def run_function(self, func: Callable[..., Any], *args: Any,
                     **kwargs: Any) -> Any:
        """Run a Python function in a sandboxed subprocess."""
        import pickle
        import base64

        # Serialize function and arguments
        payload = base64.b64encode(pickle.dumps((func, args, kwargs))).decode()

        # Create wrapper script
        wrapper = f"""
import pickle, base64, sys
payload = base64.b64decode('{payload}')
func, args, kwargs = pickle.loads(payload)
result = func(*args, **kwargs)
print(base64.b64encode(pickle.dumps(result)).decode())
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(wrapper)
            wrapper_path = f.name

        try:
            result = self.run(["python", wrapper_path])
            if result.returncode == 0 and result.stdout.strip():
                return pickle.loads(base64.b64decode(result.stdout.strip()))
            raise RuntimeError(f"Sandbox execution failed: {result.stderr}")
        finally:
            os.unlink(wrapper_path)

    def create_isolated_dir(self) -> Path:
        """Create an isolated working directory."""
        return Path(tempfile.mkdtemp(prefix="agentos_isolated_"))
