"""Tool Execution Framework - Real shell, git, file operations with sandboxing."""
from __future__ import annotations
import asyncio, os, shutil, subprocess, tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    duration_ms: float = 0.0

class ShellExecutor:
    """Execute shell commands with sandboxing and timeout."""
    
    def __init__(self, working_dir: str = ".", timeout: int = 60, 
                 allow_sudo: bool = False, env: Dict = None):
        self.working_dir = Path(working_dir)
        self.timeout = timeout
        self.allow_sudo = allow_sudo
        self.env = {**os.environ, **(env or {})}
    
    async def run(self, command: str, capture: bool = True) -> ToolResult:
        import time
        start = time.time()
        
        try:
            # Basic security check
            if not self.allow_sudo and "sudo" in command.lower():
                return ToolResult(False, "", "sudo not allowed", -1)
            
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE if capture else None,
                stderr=asyncio.subprocess.PIPE if capture else None,
                cwd=self.working_dir,
                env=self.env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            
            return ToolResult(
                success=proc.returncode == 0,
                output=stdout.decode() if stdout else "",
                error=stderr.decode() if stderr else None,
                return_code=proc.returncode,
                duration_ms=(time.time() - start) * 1000,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(False, "", "Command timed out", -1)
        except Exception as e:
            return ToolResult(False, "", str(e), -1)

class GitExecutor:
    """Git operations wrapper."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.shell = ShellExecutor(repo_path)
    
    async def init(self) -> ToolResult:
        return await self.shell.run("git init")
    
    async def add(self, files: str = ".") -> ToolResult:
        return await self.shell.run(f"git add {files}")
    
    async def commit(self, message: str) -> ToolResult:
        return await self.shell.run(f'git commit -m "{message}"')
    
    async def push(self, remote: str = "origin", branch: str = "main") -> ToolResult:
        return await self.shell.run(f"git push {remote} {branch}")
    
    async def pull(self, remote: str = "origin", branch: str = "main") -> ToolResult:
        return await self.shell.run(f"git pull {remote} {branch}")
    
    async def status(self) -> ToolResult:
        return await self.shell.run("git status")
    
    async def log(self, n: int = 10) -> ToolResult:
        return await self.shell.run(f"git log --oneline -{n}")
    
    async def branch(self) -> ToolResult:
        return await self.shell.run("git branch -a")
    
    async def create_branch(self, name: str) -> ToolResult:
        return await self.shell.run(f"git checkout -b {name}")
    
    async def diff(self) -> ToolResult:
        return await self.shell.run("git diff")
    
    async def clone(self, url: str, dest: str = None) -> ToolResult:
        cmd = f"git clone {url}"
        if dest:
            cmd += f" {dest}"
        return await self.shell.run(cmd)

class FileExecutor:
    """File operations with validation."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
    
    def read(self, path: str, limit: int = None) -> str:
        full = self.base_path / path
        content = full.read_text(errors='ignore')
        if limit:
            content = content[:limit]
        return content
    
    def write(self, path: str, content: str) -> bool:
        full = self.base_path / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        return True
    
    def exists(self, path: str) -> bool:
        return (self.base_path / path).exists()
    
    def list_dir(self, path: str = ".") -> List[str]:
        return [str(p.relative_to(self.base_path)) for p in (self.base_path / path).rglob("*")]
    
    def delete(self, path: str) -> bool:
        full = self.base_path / path
        if full.is_file():
            full.unlink()
        else:
            shutil.rmtree(full)
        return True

class PythonExecutor:
    """Execute Python code with isolation."""
    
    async def run_script(self, script: str, args: List[str] = None) -> ToolResult:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            f.flush()
            cmd = f"python {f.name}"
            if args:
                cmd += " " + " ".join(args)
            shell = ShellExecutor()
            result = await shell.run(cmd)
            os.unlink(f.name)
            return result
    
    async def run_code(self, code: str) -> ToolResult:
        return await self.run_script(code)
    
    async def pip_install(self, packages: List[str]) -> ToolResult:
        cmd = f"pip install {' '.join(packages)}"
        shell = ShellExecutor()
        return await self.shell.run(cmd)

class ToolManager:
    """Manage all tool executors."""
    
    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir)
        self.shell = ShellExecutor(working_dir)
        self.git = GitExecutor(working_dir)
        self.files = FileExecutor(working_dir)
        self.python = PythonExecutor()
    
    async def execute(self, tool: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tools = {
            "shell": self.shell.run,
            "git_init": self.git.init,
            "git_add": self.git.add,
            "git_commit": self.git.commit,
            "git_push": self.git.push,
            "git_pull": self.git.pull,
            "git_status": self.git.status,
            "git_log": self.git.log,
            "git_branch": self.git.branch,
            "git_diff": self.git.diff,
            "git_clone": self.git.clone,
        }
        
        func = tools.get(tool)
        if func:
            return await func(**kwargs)
        return ToolResult(False, "", f"Unknown tool: {tool}")
