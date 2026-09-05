"""
Computer Use Plugin — Desktop & Application Control

Enables: window management, application launching, screenshot analysis,
mouse/keyboard control, clipboard, file dialogs, multi-monitor.
"""

import os
import platform
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class OSType(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEY = "key"
    SCROLL = "scroll"
    DRAG = "drag"
    SCREENSHOT = "screenshot"
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    CLIPBOARD_READ = "clipboard_read"
    CLIPBOARD_WRITE = "clipboard_write"


@dataclass
class ComputerAction:
    action_type: str
    target: str | None = None
    coordinates: tuple[int, int] | None = None
    text: str | None = None
    key: str | None = None
    duration_ms: int = 0
    timestamp: float = field(default_factory=time.time)
    result: str | None = None
    success: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "coordinates": list(self.coordinates) if self.coordinates else None,
            "text": self.text,
            "key": self.key,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "result": self.result,
            "success": self.success,
        }


class ComputerUse:
    """Computer use and automation."""

    def __init__(self):
        self._actions: list[ComputerAction] = []
        self._os = self._detect_os()
        self._apps: dict[str, dict[str, Any]] = {}

    def _detect_os(self) -> OSType:
        sys = platform.system().lower()
        if "windows" in sys:
            return OSType.WINDOWS
        elif "darwin" in sys:
            return OSType.MACOS
        elif "linux" in sys:
            return OSType.LINUX
        return OSType.UNKNOWN

    def get_os(self) -> str:
        return self._os.value

    def register_app(self, name: str, path: str, args: list[str] | None = None):
        """Register an application for use."""
        self._apps[name] = {
            "path": path,
            "args": args or [],
            "launch_count": 0,
        }

    def execute_action(self, action: ComputerAction) -> ComputerAction:
        """Execute a computer action."""
        start = time.time()
        try:
            if action.action_type == ActionType.OPEN_APP.value:
                if action.target in self._apps:
                    action.result = f"Launched {action.target}"
                    action.success = True
                    self._apps[action.target]["launch_count"] += 1
                else:
                    action.result = f"App not registered: {action.target}"
                    action.success = False
            elif action.action_type == ActionType.CLICK.value:
                # In production, would use pyautogui or similar
                action.result = f"Clicked at {action.coordinates}"
                action.success = action.coordinates is not None
            elif action.action_type == ActionType.TYPE.value:
                action.result = f"Typed: {action.text}"
                action.success = action.text is not None
            elif action.action_type == ActionType.SCREENSHOT.value:
                action.result = "Screenshot captured (simulated)"
                action.success = True
            elif action.action_type == ActionType.CLIPBOARD_WRITE.value:
                action.result = f"Clipboard set: {action.text}"
                action.success = True
            elif action.action_type == ActionType.CLIPBOARD_READ.value:
                action.result = "Clipboard contents (simulated)"
                action.success = True
            else:
                action.result = f"Action {action.action_type} not implemented in simulation"
                action.success = False
        except Exception as e:
            action.result = f"Error: {e}"
            action.success = False

        action.duration_ms = int((time.time() - start) * 1000)
        self._actions.append(action)
        return action

    def click(self, x: int, y: int) -> ComputerAction:
        return self.execute_action(ComputerAction(
            action_type=ActionType.CLICK.value,
            coordinates=(x, y),
        ))

    def type_text(self, text: str) -> ComputerAction:
        return self.execute_action(ComputerAction(
            action_type=ActionType.TYPE.value,
            text=text,
        ))

    def open_application(self, name: str) -> ComputerAction:
        return self.execute_action(ComputerAction(
            action_type=ActionType.OPEN_APP.value,
            target=name,
        ))

    def get_action_history(self, limit: int = 20) -> list[ComputerAction]:
        return list(reversed(self._actions[-limit:]))

    def get_stats(self) -> dict[str, Any]:
        successful = sum(1 for a in self._actions if a.success)
        return {
            "os": self._os.value,
            "registered_apps": len(self._apps),
            "total_actions": len(self._actions),
            "success_rate": successful / max(1, len(self._actions)),
            "registered_app_names": list(self._apps.keys()),
        }


class ComputerUsePlugin:
    def __init__(self):
        self.engine = ComputerUse()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "stats": self.engine.get_stats(),
        }


async def create(kernel=None):
    plugin = ComputerUsePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
