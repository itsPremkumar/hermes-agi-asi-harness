#!/usr/bin/env python3
"""
HTTP Tool Plugin — Async HTTP client with retry and caching
============================================================
Features:
- Async HTTP requests (GET, POST, PUT, DELETE, PATCH)
- Automatic retry with exponential backoff
- Response caching
- Timeout handling
- Custom headers and auth
- JSON/form data support
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("hermes_http_tool")

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


class HTTPTool:
    """Async HTTP client with retry and caching."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: Dict[str, Any] = {}
    
    def _cache_key(self, url: str, method: str, data: Any = None) -> str:
        """Generate cache key."""
        key = f"{method}:{url}"
        if data:
            key += f":{hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()}"
        return key
    
    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        data: Any = None,
        json_data: Dict = None,
        timeout: int = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Make an HTTP request."""
        import urllib.request
        import urllib.error
        
        cache_key = self._cache_key(url, method, json_data or data)
        
        # Check cache for GET requests
        if method == "GET" and use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < 300:  # 5 min cache
                return cached["response"]
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, method=method)
                
                if headers:
                    for key, value in headers.items():
                        req.add_header(key, value)
                
                if json_data:
                    req.add_header("Content-Type", "application/json")
                    req.data = json.dumps(json_data).encode("utf-8")
                elif data:
                    if isinstance(data, dict):
                        req.add_header("Content-Type", "application/x-www-form-urlencoded")
                        req.data = urllib.parse.urlencode(data).encode("utf-8")
                    elif isinstance(data, str):
                        req.data = data.encode("utf-8")
                    elif isinstance(data, bytes):
                        req.data = data
                
                loop = asyncio.get_event_loop()
                
                def _fetch():
                    with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                        return resp.read().decode("utf-8", errors="replace"), resp.status, dict(resp.headers)
                
                body, status, resp_headers = await loop.run_in_executor(None, _fetch)
                
                response = {
                    "success": True,
                    "status": status,
                    "body": body,
                    "headers": resp_headers,
                    "url": url,
                    "method": method,
                }
                
                # Cache GET responses
                if method == "GET" and use_cache:
                    self._cache[cache_key] = {
                        "response": response,
                        "timestamp": time.time(),
                    }
                
                return response
                
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)
        
        return {
            "success": False,
            "error": str(last_error),
            "url": url,
            "method": method,
        }
    
    async def get(self, url: str, headers: Dict = None) -> Dict[str, Any]:
        """GET request."""
        return await self.request(url, "GET", headers=headers)
    
    async def post(self, url: str, json_data: Dict = None, data: Any = None, headers: Dict = None) -> Dict[str, Any]:
        """POST request."""
        return await self.request(url, "POST", headers=headers, data=data, json_data=json_data)
    
    async def put(self, url: str, json_data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """PUT request."""
        return await self.request(url, "PUT", headers=headers, json_data=json_data)
    
    async def delete(self, url: str, headers: Dict = None) -> Dict[str, Any]:
        """DELETE request."""
        return await self.request(url, "DELETE", headers=headers)
    
    def clear_cache(self):
        """Clear the cache."""
        self._cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """HTTP Tool Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="http_tool",
            version="1.0.0",
            description="Async HTTP client with retry, caching, and timeout handling",
            license="MIT",
            source="internal",
            capabilities=["http_get", "http_post", "http_put", "http_delete", "http_request", "api_call"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="project",
                filesystem_write="project",
                network_domains=["*"],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.tool: Optional[HTTPTool] = None
    
    async def load(self) -> bool:
        self.tool = HTTPTool()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.tool:
            self.tool = HTTPTool()
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
    
    async def get(self, url: str, headers: Dict = None) -> Dict[str, Any]:
        return await self.tool.get(url, headers)
    
    async def post(self, url: str, json_data: Dict = None, data: Any = None, headers: Dict = None) -> Dict[str, Any]:
        return await self.tool.post(url, json_data, data, headers)
    
    async def put(self, url: str, json_data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        return await self.tool.put(url, json_data, headers)
    
    async def delete(self, url: str, headers: Dict = None) -> Dict[str, Any]:
        return await self.tool.delete(url, headers)
    
    async def request(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        return await self.tool.request(url, method, **kwargs)
    
    def clear_cache(self):
        self.tool.clear_cache()
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
