#!/usr/bin/env python3
"""
Filesystem Tool Plugin — Safe file operations
==============================================
Features:
- Read/write/edit files with permission checks
- Directory listing and traversal
- File search by name or content
- File metadata and stats
- Safe path validation
"""

from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
import shutil
import stat
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_filesystem_tool")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


class FilesystemTool:
    """Safe file operations with path validation."""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
    
    def _safe_path(self, path: str) -> Optional[Path]:
        """Validate and resolve a path within root_dir."""
        try:
            full_path = (self.root_dir / path).resolve()
            # Ensure path is within root_dir
            full_path.relative_to(self.root_dir)
            return full_path
        except (ValueError, RuntimeError):
            return None
    
    def read(self, path: str, offset: int = 0, limit: int = 2000) -> Dict[str, Any]:
        """Read a file."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}
        
        try:
            if not safe_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            content = safe_path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            
            total_lines = len(lines)
            selected_lines = lines[offset:offset + limit]
            
            return {
                "success": True,
                "content": "\n".join(selected_lines),
                "total_lines": total_lines,
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < total_lines,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}
        
        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(safe_path), "bytes_written": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def edit(self, path: str, old_string: str, new_string: str) -> Dict[str, Any]:
        """Edit a file by replacing a string."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}
        
        try:
            if not safe_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            content = safe_path.read_text(encoding="utf-8")
            count = content.count(old_string)
            
            if count == 0:
                return {"success": False, "error": "String not found in file"}
            if count > 1:
                return {"success": False, "error": f"String found {count} times — provide more context for uniqueness"}
            
            new_content = content.replace(old_string, new_string, 1)
            safe_path.write_text(new_content, encoding="utf-8")
            
            return {"success": True, "path": str(safe_path), "replacements": 1}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        """List directory contents."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}
        
        try:
            if not safe_path.exists():
                return {"success": False, "error": f"Directory not found: {path}"}
            
            entries = []
            for entry in safe_path.iterdir():
                try:
                    stat_result = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "path": str(entry.relative_to(self.root_dir)),
                        "is_dir": entry.is_dir(),
                        "is_file": entry.is_file(),
                        "size": stat_result.st_size,
                        "modified": datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
                    })
                except Exception:
                    continue
            
            return {"success": True, "entries": entries, "count": len(entries)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_files(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        """Search files by glob pattern."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}
        
        try:
            matches = list(safe_path.rglob(pattern))
            results = []
            for match in matches[:100]:  # Limit results
                try:
                    results.append({
                        "path": str(match.relative_to(self.root_dir)),
                        "is_dir": match.is_dir(),
                        "size": match.stat().st_size if match.is_file() else 0,
                    })
                except Exception:
                    continue
            
            return {"success": True, "matches": results, "count": len(results)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def file_info(self, path: str) -> Dict[str, Any]:
        """Get file metadata."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}
        
        try:
            if not safe_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            stat_result = safe_path.stat()
            return {
                "success": True,
                "path": str(safe_path.relative_to(self.root_dir)),
                "exists": True,
                "is_file": safe_path.is_file(),
                "is_dir": safe_path.is_dir(),
                "size": stat_result.st_size,
                "permissions": oct(stat.S_IMODE(stat_result.st_mode)),
                "modified": datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat_result.st_ctime).isoformat(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete(self, path: str) -> Dict[str, Any]:
        """Delete a file or directory."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}
        
        try:
            if not safe_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            if safe_path.is_dir():
                shutil.rmtree(safe_path)
            else:
                safe_path.unlink()
            
            return {"success": True, "path": str(safe_path.relative_to(self.root_dir))}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def copy(self, src: str, dst: str) -> Dict[str, Any]:
        """Copy a file or directory."""
        safe_src = self._safe_path(src)
        safe_dst = self._safe_path(dst)
        
        if not safe_src or not safe_dst:
            return {"success": False, "error": "Invalid path"}
        
        try:
            if not safe_src.exists():
                return {"success": False, "error": f"Source not found: {src}"}
            
            if safe_src.is_dir():
                shutil.copytree(safe_src, safe_dst)
            else:
                shutil.copy2(safe_src, safe_dst)
            
            return {"success": True, "src": src, "dst": dst}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move(self, src: str, dst: str) -> Dict[str, Any]:
        """Move a file or directory."""
        safe_src = self._safe_path(src)
        safe_dst = self._safe_path(dst)
        
        if not safe_src or not safe_dst:
            return {"success": False, "error": "Invalid path"}
        
        try:
            if not safe_src.exists():
                return {"success": False, "error": f"Source not found: {src}"}
            
            shutil.move(str(safe_src), str(safe_dst))
            return {"success": True, "src": src, "dst": dst}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Filesystem Tool Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="filesystem_tool",
            version="1.0.0",
            description="Safe file operations with path validation, read/write/edit, directory listing, and file search",
            license="MIT",
            source="internal",
            capabilities=["file_read", "file_write", "file_edit", "file_delete", "directory_list", "file_search"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.tool: Optional[FilesystemTool] = None
    
    async def load(self) -> bool:
        self.tool = FilesystemTool()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.tool:
            self.tool = FilesystemTool()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.tool is not None,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def read(self, path: str, offset: int = 0, limit: int = 2000) -> Dict[str, Any]:
        return self.tool.read(path, offset, limit)
    
    def write(self, path: str, content: str) -> Dict[str, Any]:
        return self.tool.write(path, content)
    
    def edit(self, path: str, old_string: str, new_string: str) -> Dict[str, Any]:
        return self.tool.edit(path, old_string, new_string)
    
    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        return self.tool.list_dir(path)
    
    def search_files(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        return self.tool.search_files(pattern, path)
    
    def file_info(self, path: str) -> Dict[str, Any]:
        return self.tool.file_info(path)
    
    def delete(self, path: str) -> Dict[str, Any]:
        return self.tool.delete(path)
    
    def copy(self, src: str, dst: str) -> Dict[str, Any]:
        return self.tool.copy(src, dst)
    
    def move(self, src: str, dst: str) -> Dict[str, Any]:
        return self.tool.move(src, dst)
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
