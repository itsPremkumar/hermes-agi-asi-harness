"""Long Autonomous Terminal Runs - Persistent terminal sessions."""
from __future__ import annotations

import asyncio
import subprocess
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class TerminalSession:
    """Persistent terminal session for long-running tasks."""
    
    def __init__(self, session_id: str, command: str, cwd: str = ".",
                 env: dict | None = None, timeout: int = 3600):
        self.session_id = session_id
        self.command = command
        self.cwd = cwd
        self.env = env or {}
        self.timeout = timeout
        self._process: subprocess.Popen | None = None
        self._output: list[str] = []
        self._running = False
        self._start_time: float = 0
    
    async def start(self) -> bool:
        """Start the terminal session."""
        try:
            self._process = subprocess.Popen(
                self.command,
                shell=True,
                cwd=self.cwd,
                env={**__import__('os').environ, **self.env},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._running = True
            self._start_time = time.time()
            
            # Start output reader
            asyncio.create_task(self._read_output())
            return True
        except Exception as e:
            self._output.append(f"Error: {e}")
            return False
    
    async def _read_output(self):
        """Read output from the process."""
        while self._running and self._process:
            line = self._process.stdout.readline()
            if line:
                self._output.append(line.strip())
            elif self._process.poll() is not None:
                break
            await asyncio.sleep(0.1)
    
    async def send_input(self, data: str):
        """Send input to the session."""
        if self._process and self._running:
            self._process.stdin.write(data + "\n")
            self._process.stdin.flush()
    
    async def get_output(self, clear: bool = False) -> list[str]:
        """Get current output."""
        output = self._output.copy()
        if clear:
            self._output = []
        return output
    
    async def stop(self):
        """Stop the session."""
        if self._process:
            self._process.terminate()
            self._process.wait()
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running and self._process and self._process.poll() is None
    
    @property
    def duration(self) -> float:
        return time.time() - self._start_time if self._start_time else 0


class BackgroundTaskManager:
    """Manage background tasks and long-running processes."""
    
    def __init__(self):
        self._tasks: dict[str, TerminalSession] = {}
        self._results: dict[str, Any] = {}
    
    async def start_task(self, command: str, cwd: str = ".",
                         env: dict | None = None, timeout: int = 3600) -> str:
        """Start a background task."""
        session_id = str(uuid.uuid4())
        session = TerminalSession(session_id, command, cwd, env, timeout)
        
        if await session.start():
            self._tasks[session_id] = session
            return session_id
        return ""
    
    async def get_output(self, task_id: str, clear: bool = False) -> list[str]:
        """Get output from a task."""
        session = self._tasks.get(task_id)
        if session:
            return await session.get_output(clear)
        return []
    
    async def stop_task(self, task_id: str):
        """Stop a background task."""
        session = self._tasks.get(task_id)
        if session:
            await session.stop()
    
    def get_running_tasks(self) -> list[dict[str, Any]]:
        """Get all running tasks."""
        return [
            {
                "id": tid,
                "command": session.command,
                "running": session.is_running,
                "duration": session.duration,
            }
            for tid, session in self._tasks.items()
        ]
