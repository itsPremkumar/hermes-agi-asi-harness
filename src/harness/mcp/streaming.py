"""MCPStreaming — streaming responses, progress updates.

Handles streaming responses from MCP servers, including progress
events, partial results, and completion notifications. Supports
both push and pull models for streaming.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


class StreamState(Enum):
    """Possible states for a stream."""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class StreamEvent:
    """An event in an MCP stream."""
    event_id: str
    stream_id: str
    event_type: str  # "progress", "result", "error", "complete"
    data: Any = None
    progress: float = 0.0  # 0.0 to 1.0
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "stream_id": self.stream_id,
            "event_type": self.event_type,
            "data": self.data,
            "progress": self.progress,
            "message": self.message,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class MCPStream:
    """A stream for receiving progress and results from MCP tools.

    Supports event callbacks, progress tracking, and cancellation.
    """

    def __init__(self, stream_id: Optional[str] = None, tool_name: str = ""):
        self._stream_id = stream_id or f"stream-{uuid.uuid4().hex[:12]}"
        self._tool_name = tool_name
        self._state = StreamState.IDLE
        self._events: List[StreamEvent] = []
        self._progress: float = 0.0
        self._result: Any = None
        self._error: Optional[str] = None
        self._created_at = time.time()
        self._completed_at: Optional[float] = None
        self._lock = threading.RLock()
        self._event_callbacks: List[Callable[[StreamEvent], None]] = []
        self._completion_callbacks: List[Callable[[Any, Optional[str]], None]] = []

    @property
    def stream_id(self) -> str:
        return self._stream_id

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def state(self) -> StreamState:
        return self._state

    @property
    def progress(self) -> float:
        return self._progress

    @property
    def result(self) -> Any:
        return self._result

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def is_active(self) -> bool:
        return self._state == StreamState.ACTIVE

    @property
    def is_complete(self) -> bool:
        return self._state in (StreamState.COMPLETED, StreamState.ERROR, StreamState.CANCELLED)

    @property
    def duration(self) -> float:
        end = self._completed_at or time.time()
        return end - self._created_at

    @property
    def events(self) -> List[StreamEvent]:
        return list(self._events)

    # -- Stream Control -----------------------------------------------------

    def start(self) -> None:
        """Start the stream."""
        with self._lock:
            self._state = StreamState.ACTIVE

    def pause(self) -> None:
        """Pause the stream."""
        with self._lock:
            if self._state == StreamState.ACTIVE:
                self._state = StreamState.PAUSED

    def resume(self) -> None:
        """Resume the stream."""
        with self._lock:
            if self._state == StreamState.PAUSED:
                self._state = StreamState.ACTIVE

    def cancel(self) -> None:
        """Cancel the stream."""
        with self._lock:
            self._state = StreamState.CANCELLED
            self._completed_at = time.time()

    def complete(self, result: Any = None) -> None:
        """Mark the stream as completed with a result."""
        with self._lock:
            self._state = StreamState.COMPLETED
            self._result = result
            self._progress = 1.0
            self._completed_at = time.time()

        # Fire completion callbacks
        for cb in self._completion_callbacks:
            try:
                cb(result, None)
            except Exception:
                pass

    def fail(self, error: str = "") -> None:
        """Mark the stream as failed with an error."""
        with self._lock:
            self._state = StreamState.ERROR
            self._error = error
            self._completed_at = time.time()

        # Fire completion callbacks
        for cb in self._completion_callbacks:
            try:
                cb(None, error)
            except Exception:
                pass

    # -- Event Handling -----------------------------------------------------

    def push_event(self, event: StreamEvent) -> None:
        """Push an event to the stream."""
        with self._lock:
            self._events.append(event)
            if event.event_type == "progress":
                self._progress = event.progress
            elif event.event_type == "result":
                self._result = event.data
            elif event.event_type == "error":
                self._error = event.message
                self._state = StreamState.ERROR

        # Fire event callbacks
        for cb in self._event_callbacks:
            try:
                cb(event)
            except Exception:
                pass

    def push_progress(self, progress: float, message: str = "") -> StreamEvent:
        """Push a progress event."""
        event = StreamEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            stream_id=self._stream_id,
            event_type="progress",
            progress=progress,
            message=message,
        )
        self.push_event(event)
        return event

    def push_result(self, data: Any) -> StreamEvent:
        """Push a result event."""
        event = StreamEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            stream_id=self._stream_id,
            event_type="result",
            data=data,
        )
        self.push_event(event)
        return event

    def on_event(self, callback: Callable[[StreamEvent], None]) -> None:
        """Register an event callback."""
        self._event_callbacks.append(callback)

    def on_complete(self, callback: Callable[[Any, Optional[str]], None]) -> None:
        """Register a completion callback: fn(result, error)."""
        self._completion_callbacks.append(callback)

    # -- Reporting ----------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the stream."""
        return {
            "stream_id": self._stream_id,
            "tool_name": self._tool_name,
            "state": self._state.value,
            "progress": self._progress,
            "event_count": len(self._events),
            "duration": self.duration,
            "has_result": self._result is not None,
            "error": self._error,
        }


class StreamingManager:
    """Manages multiple MCP streams."""

    def __init__(self):
        self._streams: Dict[str, MCPStream] = {}
        self._tool_streams: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def create_stream(self, tool_name: str = "", stream_id: Optional[str] = None) -> MCPStream:
        """Create a new stream."""
        stream = MCPStream(stream_id=stream_id, tool_name=tool_name)
        with self._lock:
            self._streams[stream.stream_id] = stream
            if tool_name:
                self._tool_streams[tool_name].add(stream.stream_id)
        return stream

    def get_stream(self, stream_id: str) -> Optional[MCPStream]:
        """Get a stream by ID."""
        return self._streams.get(stream_id)

    def get_streams_for_tool(self, tool_name: str) -> List[MCPStream]:
        """Get all streams for a tool."""
        ids = self._tool_streams.get(tool_name, set())
        return [self._streams[sid] for sid in ids if sid in self._streams]

    def get_active_streams(self) -> List[MCPStream]:
        """Get all active streams."""
        return [s for s in self._streams.values() if s.is_active]

    def cancel_all(self, tool_name: Optional[str] = None) -> int:
        """Cancel streams. If tool_name is given, cancel only that tool's streams."""
        with self._lock:
            if tool_name:
                streams = self.get_streams_for_tool(tool_name)
            else:
                streams = list(self._streams.values())

            cancelled = 0
            for stream in streams:
                if stream.is_active:
                    stream.cancel()
                    cancelled += 1
            return cancelled

    def cleanup_completed(self) -> int:
        """Remove completed streams. Returns the count removed."""
        with self._lock:
            to_remove = [
                sid for sid, s in self._streams.items()
                if s.is_complete
            ]
            for sid in to_remove:
                stream = self._streams.pop(sid)
                if stream.tool_name:
                    self._tool_streams[stream.tool_name].discard(sid)
            return len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        states: Dict[str, int] = defaultdict(int)
        for s in self._streams.values():
            states[s._state.value] += 1

        return {
            "total_streams": len(self._streams),
            "active_streams": len(self.get_active_streams()),
            "state_breakdown": dict(states),
            "tools_with_streams": len(self._tool_streams),
        }
