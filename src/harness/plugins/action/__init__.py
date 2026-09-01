"""Action Plugins — ToolUse, CodeGen, Web, FileSystem, Shell, API."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginMetadata:
    provides: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)


class BasePlugin:
    def __init__(self, plugin_id: str, provides: list[str]):
        self.id = plugin_id
        self.metadata = PluginMetadata(provides=provides)
        self._loaded = False

    def on_load(self) -> None:
        self._loaded = True

    def on_unload(self) -> None:
        self._loaded = False

    def health_check(self) -> dict[str, Any]:
        return {"healthy": self._loaded}


class ToolUsePlugin(BasePlugin):
    def __init__(self):
        super().__init__("action.tool_use", ["tools", "function_calling", "execution"])

    def execute(self, tool: str, args: dict) -> dict[str, Any]:
        return {"result": f"executed {tool}", "args": args}


class CodeGenPlugin(BasePlugin):
    def __init__(self):
        super().__init__("action.code_gen", ["code", "generation", "synthesis"])

    def generate(self, spec: str) -> dict[str, Any]:
        return {"code": f"# {spec}\npass", "language": "python"}


class WebPlugin(BasePlugin):
    def __init__(self):
        super().__init__("action.web", ["web", "http", "fetch"])

    def fetch(self, url: str) -> dict[str, Any]:
        return {"status": 200, "content": f"Content from {url}"}


class FileSystemPlugin(BasePlugin):
    def __init__(self):
        super().__init__("action.filesystem", ["fs", "read", "write"])

    def read(self, path: str) -> dict[str, Any]:
        return {"content": f"Content of {path}"}

    def write(self, path: str, content: str) -> dict[str, Any]:
        return {"written": True, "path": path}


class ShellPlugin(BasePlugin):
    def __init__(self):
        super().__init__("action.shell", ["shell", "exec", "command"])

    def run(self, command: str) -> dict[str, Any]:
        return {"stdout": f"Output of {command}", "returncode": 0}


class APIPlugin(BasePlugin):
    def __init__(self):
        super().__init__("action.api", ["api", "rest", "graphql"])

    def call(self, endpoint: str, method: str = "GET") -> dict[str, Any]:
        return {"status": 200, "data": {"endpoint": endpoint, "method": method}}
