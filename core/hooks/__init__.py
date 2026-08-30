"""Hooks & Customization System - Pre/post command hooks, slash commands."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


class HookType(str, Enum):
    PRE_COMMAND = "pre_command"
    POST_COMMAND = "post_command"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"


@dataclass
class Hook:
    id: str
    hook_type: HookType
    pattern: str  # Regex pattern to match command
    action: Callable
    description: str = ""
    enabled: bool = True


class HookManager:
    """Manage hooks for customizing agent behavior."""
    
    def __init__(self):
        self._hooks: List[Hook] = []
    
    def register(self, hook_type: HookType, pattern: str, action: Callable, description: str = ""):
        import uuid
        self._hooks.append(Hook(
            id=str(uuid.uuid4()),
            hook_type=hook_type,
            pattern=pattern,
            action=action,
            description=description,
        ))
    
    async def execute(self, hook_type: HookType, command: str, context: Dict = None) -> bool:
        """Execute hooks matching a command."""
        for hook in self._hooks:
            if hook.hook_type == hook_type and hook.enabled:
                if re.search(hook.pattern, command):
                    result = await hook.action(command, context or {})
                    if result is False:
                        return False
        return True


class SlashCommand:
    """Custom slash command."""
    
    def __init__(self, name: str, description: str, handler: Callable):
        self.name = name
        self.description = description
        self.handler = handler
    
    async def execute(self, args: str) -> str:
        return await self.handler(args)


class SlashCommandRegistry:
    """Registry for slash commands."""
    
    def __init__(self):
        self._commands: Dict[str, SlashCommand] = {}
    
    def register(self, name: str, description: str, handler: Callable):
        self._commands[name] = SlashCommand(name, description, handler)
    
    def get(self, name: str) -> Optional[SlashCommand]:
        return self._commands.get(name)
    
    def list_commands(self) -> List[Dict[str, str]]:
        return [{"name": c.name, "description": c.description} for c in self._commands.values()]
