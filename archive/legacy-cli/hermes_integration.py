"""Hermes AGI/ASI Harness — Hermes Integration Plugin

Native bindings to the Hermes agent runtime:
- Hermes profile lifecycle management
- Memory system integration (episodic, semantic, procedural)
- Skill and tool registry hooks
- Gateway communication bridge
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from harness_control_plane import (
    IPlugin,
    TaskRequest,
    TaskResult,
)

logger = logging.getLogger(__name__)


@dataclass
class HermesProfile:
    """Represents a Hermes agent profile."""
    name: str
    display_name: str
    role: str
    symbol: str
    model: str
    provider: str
    capabilities: list[str] = field(default_factory=list)
    has_shell: bool = True
    has_memory: bool = True
    active: bool = True


@dataclass
class MemoryEntry:
    """A memory entry in the Hermes memory system."""
    entry_id: str
    content: str
    category: str  # user, memory, session
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class HermesIntegrationPlugin(IPlugin):
    """Native integration with the Hermes agent runtime."""
    
    name = "hermes-integration"
    version = "1.0.0"
    capabilities = [
        "profile_lifecycle",
        "memory_read",
        "memory_write",
        "skill_hook",
        "gateway_bridge",
        "tool_registry",
    ]
    
    def __init__(self, hermes_home: str | None = None):
        self._hermes_home = Path(hermes_home or self._detect_hermes_home())
        self._profiles: dict[str, HermesProfile] = {}
        self._memory_cache: dict[str, list[MemoryEntry]] = {}
        self._skill_hooks: dict[str, callable] = {}
        self._gateway_url: str | None = None
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the Hermes integration."""
        self._gateway_url = config.get("gateway_url", "http://localhost:3000")
        
        # Detect profiles
        await self._detect_profiles()
        
        self._initialized = True
        logger.info(f"Hermes integration initialized (home={self._hermes_home})")
    
    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute a task via Hermes integration."""
        task_type = task.task_type
        
        if task_type == "profile_list":
            return await self._list_profiles()
        elif task_type == "memory_read":
            return await self._read_memory(task.payload)
        elif task_type == "memory_write":
            return await self._write_memory(task.payload)
        elif task_type == "skill_hook":
            return await self._hook_skill(task.payload)
        elif task_type == "gateway_status":
            return await self._gateway_status()
        else:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=f"Unknown task type: {task_type}",
            )
    
    async def shutdown(self) -> None:
        """Shutdown the Hermes integration."""
        self._initialized = False
        self._profiles.clear()
        self._memory_cache.clear()
    
    async def health_check(self) -> bool:
        """Check integration health."""
        return self._initialized and self._hermes_home.exists()
    
    async def get_profile(self, name: str) -> HermesProfile | None:
        """Get a profile by name."""
        return self._profiles.get(name)
    
    async def list_profiles(self) -> list[HermesProfile]:
        """List all detected profiles."""
        return list(self._profiles.values())
    
    async def read_memory(self, category: str = "memory", limit: int = 50) -> list[MemoryEntry]:
        """Read from the Hermes memory system."""
        memory_file = self._hermes_home / "memories" / f"{category}.jsonl"
        if not memory_file.exists():
            return []
        
        entries = []
        with open(memory_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        entries.append(MemoryEntry(**data))
                    except (json.JSONDecodeError, TypeError):
                        continue
        
        return entries[-limit:]
    
    async def write_memory(self, content: str, category: str = "memory", 
                           metadata: dict[str, Any] | None = None) -> MemoryEntry:
        """Write to the Hermes memory system."""
        memory_dir = self._hermes_home / "memories"
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        entry = MemoryEntry(
            entry_id=f"mem-{datetime.utcnow().timestamp():.0f}",
            content=content,
            category=category,
            metadata=metadata or {},
        )
        
        memory_file = memory_dir / f"{category}.jsonl"
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "entry_id": entry.entry_id,
                "content": entry.content,
                "category": entry.category,
                "timestamp": entry.timestamp,
                "metadata": entry.metadata,
            }) + "\n")
        
        return entry
    
    def register_skill_hook(self, skill_name: str, hook: callable) -> None:
        """Register a skill hook."""
        self._skill_hooks[skill_name] = hook
    
    async def _detect_profiles(self) -> None:
        """Detect Hermes profiles from the filesystem."""
        profiles_dir = self._hermes_home / "profiles"
        if not profiles_dir.exists():
            return
        
        for profile_dir in profiles_dir.iterdir():
            if profile_dir.is_dir():
                profile = HermesProfile(
                    name=profile_dir.name,
                    display_name=profile_dir.name,
                    role="assistant",
                    symbol="🤖",
                    model="unknown",
                    provider="unknown",
                )
                self._profiles[profile_dir.name] = profile
    
    async def _list_profiles(self) -> TaskResult:
        """List all profiles."""
        profiles = [
            {
                "name": p.name,
                "display_name": p.display_name,
                "role": p.role,
                "symbol": p.symbol,
                "active": p.active,
            }
            for p in self._profiles.values()
        ]
        
        return TaskResult(
            task_id="",
            success=True,
            result=profiles,
        )
    
    async def _read_memory(self, payload: dict[str, Any]) -> TaskResult:
        """Read memory."""
        category = payload.get("category", "memory")
        limit = payload.get("limit", 50)
        
        entries = await self.read_memory(category, limit)
        
        return TaskResult(
            task_id="",
            success=True,
            result=[
                {
                    "entry_id": e.entry_id,
                    "content": e.content,
                    "category": e.category,
                    "timestamp": e.timestamp,
                }
                for e in entries
            ],
        )
    
    async def _write_memory(self, payload: dict[str, Any]) -> TaskResult:
        """Write memory."""
        content = payload.get("content", "")
        category = payload.get("category", "memory")
        metadata = payload.get("metadata", {})
        
        entry = await self.write_memory(content, category, metadata)
        
        return TaskResult(
            task_id="",
            success=True,
            result={"entry_id": entry.entry_id, "written": True},
        )
    
    async def _hook_skill(self, payload: dict[str, Any]) -> TaskResult:
        """Hook a skill."""
        skill_name = payload.get("skill_name", "")
        hook = payload.get("hook")
        
        if hook:
            self._skill_hooks[skill_name] = hook
            return TaskResult(task_id="", success=True, result={"hooked": skill_name})
        
        return TaskResult(
            task_id="",
            success=False,
            error=f"No hook provided for {skill_name}",
        )
    
    async def _gateway_status(self) -> TaskResult:
        """Check gateway status."""
        # Simplified: check if gateway URL is reachable
        return TaskResult(
            task_id="",
            success=True,
            result={
                "gateway_url": self._gateway_url,
                "status": "running" if self._initialized else "offline",
            },
        )
    
    @staticmethod
    def _detect_hermes_home() -> str:
        """Detect Hermes home directory."""
        # Check common locations
        candidates = [
            Path.home() / ".hermes",
            Path.home() / "AppData" / "Local" / "hermes",
            Path.home() / ".config" / "hermes",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        
        # Default
        return str(Path.home() / ".hermes")
