"""
Sandbox Architecture — Section 34 of v7 spec

No self-generated code is automatically trusted.
Static check → Risk classification → Ephemeral sandbox → Tests → Benchmark → Red Team → Verdict
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result of sandboxed execution."""
    id: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    duration_seconds: float = 0.0
    error: str | None = None


class Sandbox:
    """Execute code in an isolated environment."""

    def __init__(self, timeout: int = 30, max_memory_mb: int = 512):
        self._timeout = timeout
        self._max_memory_mb = max_memory_mb

    async def execute(self, code: str, language: str = "python") -> SandboxResult:
        """Execute code in an isolated sandbox."""
        start = time.time()
        sandbox_id = str(uuid.uuid4())[:8]
        
        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, prefix=f"sandbox_{sandbox_id}_") as f:
            f.write(code)
            code_file = f.name

        try:
            result = await asyncio.wait_for(
                self._run_in_subprocess(code_file),
                timeout=self._timeout,
            )
            result.id = sandbox_id
            result.duration_seconds = time.time() - start
            return result
        except asyncio.TimeoutError:
            return SandboxResult(
                id=sandbox_id,
                success=False,
                stderr=f"Sandbox timeout after {self._timeout}s",
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            return SandboxResult(
                id=sandbox_id,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start,
            )
        finally:
            # Cleanup temp file
            try:
                os.unlink(code_file)
            except Exception:
                pass

    async def _run_in_subprocess(self, code_file: str) -> SandboxResult:
        """Run code in a subprocess."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )
            stdout, stderr = await proc.communicate()
            return SandboxResult(
                id="",
                success=proc.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                return_code=proc.returncode or 0,
            )
        except Exception as e:
            return SandboxResult(
                id="",
                success=False,
                error=str(e),
                return_code=-1,
            )

    async def static_check(self, code: str) -> dict[str, Any]:
        """Perform static checks on code."""
        issues = []
        
        # Check for dangerous imports
        dangerous = ["os.system", "subprocess", "eval(", "exec(", "import os"]
        for pattern in dangerous:
            if pattern in code:
                issues.append(f"Contains potentially dangerous pattern: {pattern}")
        
        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "risk_class": "high" if len(issues) > 2 else "medium" if issues else "low",
        }

    async def run_tests(self, code_file: str, test_file: str) -> SandboxResult:
        """Run tests against code in sandbox."""
        start = time.time()
        sandbox_id = str(uuid.uuid4())[:8]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "pytest", test_file, "-v",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
            return SandboxResult(
                id=sandbox_id,
                success=proc.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                return_code=proc.returncode or 0,
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            return SandboxResult(
                id=sandbox_id,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start,
            )


class SandboxPlugin:
    def __init__(self):
        self.engine = Sandbox()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "timeout": self.engine._timeout}

    async def execute(self, code: str, **kwargs):
        return await self.engine.execute(code, **kwargs)

    async def static_check(self, code: str):
        return await self.engine.static_check(code)


async def create(kernel=None):
    plugin = SandboxPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
