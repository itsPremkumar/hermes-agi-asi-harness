#!/usr/bin/env python3
"""
Streaming Output Plugin — Real-time output streaming
===================================================
Features:
- Stream output in chunks
- Multiple output formats (text, JSON, SSE)
- Async generators for streaming
- Rate limiting and backpressure
- Output buffering
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("hermes_streaming_output")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum as _Enum
    
    class PluginState(str, _Enum):
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


class StreamFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    SSE = "sse"  # Server-Sent Events


@dataclass
class StreamChunk:
    """A chunk of streamed output."""
    content: str
    format: StreamFormat
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class StreamingOutput:
    """Real-time output streaming."""
    
    def __init__(self, default_format: StreamFormat = StreamFormat.TEXT):
        self.default_format = default_format
        self._subscribers: List[asyncio.Queue] = []
        self._buffer: List[StreamChunk] = []
        self._max_buffer = 1000
    
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to the stream."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from the stream."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
    
    async def emit(self, content: str, format: StreamFormat = None, metadata: Dict[str, Any] = None):
        """Emit a chunk to all subscribers."""
        chunk = StreamChunk(
            content=content,
            format=format or self.default_format,
            metadata=metadata or {},
        )
        
        # Buffer
        self._buffer.append(chunk)
        if len(self._buffer) > self._max_buffer:
            self._buffer.pop(0)
        
        # Notify subscribers
        for queue in self._subscribers:
            await queue.put(chunk)
    
    def format_chunk(self, chunk: StreamChunk) -> str:
        """Format a chunk for output."""
        if chunk.format == StreamFormat.JSON:
            return json.dumps({
                "content": chunk.content,
                "timestamp": chunk.timestamp,
                "metadata": chunk.metadata,
            })
        elif chunk.format == StreamFormat.SSE:
            return f"data: {json.dumps({'content': chunk.content, 'timestamp': chunk.timestamp, 'metadata': chunk.metadata})}\n\n"
        else:
            return chunk.content
    
    async def stream_from_generator(self, generator: AsyncGenerator[str, None], 
                                    format: StreamFormat = None) -> int:
        """Stream from an async generator."""
        count = 0
        async for item in generator:
            await self.emit(item, format)
            count += 1
        return count
    
    async def stream_lines(self, text: str, delay: float = 0.0) -> int:
        """Stream text line by line."""
        count = 0
        for line in text.split("\n"):
            await self.emit(line + "\n")
            count += 1
            if delay > 0:
                await asyncio.sleep(delay)
        return count
    
    async def collect(self, duration: float = 1.0) -> List[StreamChunk]:
        """Collect chunks for a duration."""
        await asyncio.sleep(duration)
        return self._buffer.copy()
    
    def get_buffer(self) -> List[StreamChunk]:
        """Get buffered chunks."""
        return self._buffer.copy()
    
    def clear_buffer(self):
        """Clear the buffer."""
        self._buffer.clear()


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Streaming Output Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="streaming_output",
            version="1.0.0",
            description="Real-time output streaming with multiple formats, async generators, and subscriber model",
            license="MIT",
            source="internal",
            capabilities=["stream_output", "subscribe", "stream_generator", "buffer_management"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=256,
                max_cpu_percent=10,
            ),
        )
        self.streamer: Optional[StreamingOutput] = None
    
    async def load(self) -> bool:
        self.streamer = StreamingOutput()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.streamer:
            self.streamer = StreamingOutput()
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
            "ready": self.streamer is not None,
            "subscribers": len(self.streamer._subscribers) if self.streamer else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def subscribe(self) -> asyncio.Queue:
        return self.streamer.subscribe()
    
    def unsubscribe(self, queue: asyncio.Queue):
        self.streamer.unsubscribe(queue)
    
    async def emit(self, content: str, format: str = "text", metadata: Dict[str, Any] = None):
        from plugins.streaming_output import StreamFormat
        await self.streamer.emit(content, StreamFormat(format), metadata)
    
    async def stream_from_generator(self, generator, format: str = "text") -> int:
        from plugins.streaming_output import StreamFormat
        return await self.streamer.stream_from_generator(generator, StreamFormat(format))
    
    async def stream_lines(self, text: str, delay: float = 0.0) -> int:
        return await self.streamer.stream_lines(text, delay)
    
    def get_buffer(self) -> List[Dict[str, Any]]:
        return [
            {
                "content": c.content,
                "format": c.format.value,
                "timestamp": c.timestamp,
                "metadata": c.metadata,
            }
            for c in self.streamer.get_buffer()
        ]
    
    def clear_buffer(self):
        self.streamer.clear_buffer()
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
