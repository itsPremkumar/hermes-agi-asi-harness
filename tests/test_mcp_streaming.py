"""Tests for MCPStreaming — streaming responses, progress updates."""
from __future__ import annotations

import pytest

from harness.mcp.streaming import (
    MCPStream,
    StreamEvent,
    StreamState,
    StreamingManager,
)


class TestStreamState:
    def test_values(self):
        assert StreamState.IDLE.value == "idle"
        assert StreamState.ACTIVE.value == "active"
        assert StreamState.PAUSED.value == "paused"
        assert StreamState.COMPLETED.value == "completed"
        assert StreamState.ERROR.value == "error"
        assert StreamState.CANCELLED.value == "cancelled"


class TestStreamEvent:
    def test_create(self):
        event = StreamEvent(
            event_id="e1",
            stream_id="s1",
            event_type="progress",
            progress=0.5,
            message="half done",
        )
        assert event.event_id == "e1"
        assert event.stream_id == "s1"
        assert event.event_type == "progress"
        assert event.progress == 0.5
        assert event.message == "half done"

    def test_to_dict(self):
        event = StreamEvent(
            event_id="e1",
            stream_id="s1",
            event_type="result",
            data={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_id"] == "e1"
        assert d["stream_id"] == "s1"
        assert d["event_type"] == "result"
        assert d["data"] == {"key": "value"}


class TestMCPStream:
    def test_create(self):
        stream = MCPStream(tool_name="search")
        assert stream.tool_name == "search"
        assert stream.state == StreamState.IDLE
        assert stream.stream_id.startswith("stream-")
        assert stream.progress == 0.0
        assert stream.is_active is False
        assert stream.is_complete is False

    def test_start(self):
        stream = MCPStream(tool_name="search")
        stream.start()
        assert stream.state == StreamState.ACTIVE
        assert stream.is_active is True

    def test_pause(self):
        stream = MCPStream(tool_name="search")
        stream.start()
        stream.pause()
        assert stream.state == StreamState.PAUSED
        assert stream.is_active is False

    def test_resume(self):
        stream = MCPStream(tool_name="search")
        stream.start()
        stream.pause()
        stream.resume()
        assert stream.state == StreamState.ACTIVE

    def test_complete(self):
        stream = MCPStream(tool_name="search")
        stream.start()
        stream.complete(result={"data": "test"})
        assert stream.state == StreamState.COMPLETED
        assert stream.is_complete is True
        assert stream.result == {"data": "test"}
        assert stream.progress == 1.0

    def test_fail(self):
        stream = MCPStream(tool_name="search")
        stream.start()
        stream.fail(error="something went wrong")
        assert stream.state == StreamState.ERROR
        assert stream.is_complete is True
        assert stream.error == "something went wrong"

    def test_cancel(self):
        stream = MCPStream(tool_name="search")
        stream.start()
        stream.cancel()
        assert stream.state == StreamState.CANCELLED
        assert stream.is_complete is True

    def test_push_event_progress(self):
        stream = MCPStream(tool_name="search")
        event = stream.push_progress(0.5, "halfway")
        assert event.event_type == "progress"
        assert stream.progress == 0.5
        assert len(stream.events) == 1

    def test_push_event_result(self):
        stream = MCPStream(tool_name="search")
        event = stream.push_result(data={"key": "value"})
        assert event.event_type == "result"
        assert stream.result == {"key": "value"}

    def test_push_event_error(self):
        stream = MCPStream(tool_name="search")
        event = StreamEvent(
            event_id="e1",
            stream_id=stream.stream_id,
            event_type="error",
            message="fail",
        )
        stream.push_event(event)
        assert stream.error == "fail"
        assert stream.state == StreamState.ERROR

    def test_on_event(self):
        stream = MCPStream(tool_name="search")
        events_received = []
        stream.on_event(lambda evt: events_received.append(evt))
        stream.push_progress(0.5)
        assert len(events_received) == 1
        assert events_received[0].progress == 0.5

    def test_on_complete(self):
        stream = MCPStream(tool_name="search")
        completed = []
        stream.on_complete(lambda result, error: completed.append((result, error)))
        stream.complete(result="done")
        assert len(completed) == 1
        assert completed[0] == ("done", None)

    def test_on_complete_error(self):
        stream = MCPStream(tool_name="search")
        completed = []
        stream.on_complete(lambda result, error: completed.append((result, error)))
        stream.fail(error="boom")
        assert len(completed) == 1
        assert completed[0] == (None, "boom")

    def test_get_summary(self):
        stream = MCPStream(tool_name="search")
        stream.start()
        stream.push_progress(0.5)
        summary = stream.get_summary()
        assert summary["state"] == "active"
        assert summary["progress"] == 0.5
        assert summary["event_count"] == 1
        assert summary["has_result"] is False

    def test_duration(self):
        stream = MCPStream(tool_name="search")
        assert stream.duration >= 0


class TestStreamingManager:
    def test_create(self):
        mgr = StreamingManager()
        assert mgr.get_stats()["total_streams"] == 0

    def test_create_stream(self):
        mgr = StreamingManager()
        stream = mgr.create_stream(tool_name="search")
        assert stream.tool_name == "search"
        assert mgr.get_stats()["total_streams"] == 1

    def test_get_stream(self):
        mgr = StreamingManager()
        stream = mgr.create_stream(tool_name="search")
        result = mgr.get_stream(stream.stream_id)
        assert result is stream

    def test_get_streams_for_tool(self):
        mgr = StreamingManager()
        s1 = mgr.create_stream(tool_name="search")
        s2 = mgr.create_stream(tool_name="search")
        s3 = mgr.create_stream(tool_name="fetch")
        results = mgr.get_streams_for_tool("search")
        assert len(results) == 2

    def test_get_active_streams(self):
        mgr = StreamingManager()
        s1 = mgr.create_stream(tool_name="search")
        s2 = mgr.create_stream(tool_name="fetch")
        s1.start()
        s2.start()
        assert len(mgr.get_active_streams()) == 2

    def test_cancel_all(self):
        mgr = StreamingManager()
        s1 = mgr.create_stream(tool_name="search")
        s2 = mgr.create_stream(tool_name="fetch")
        s1.start()
        s2.start()
        cancelled = mgr.cancel_all()
        assert cancelled == 2

    def test_cancel_all_for_tool(self):
        mgr = StreamingManager()
        s1 = mgr.create_stream(tool_name="search")
        s2 = mgr.create_stream(tool_name="fetch")
        s1.start()
        s2.start()
        cancelled = mgr.cancel_all(tool_name="search")
        assert cancelled == 1

    def test_cleanup_completed(self):
        mgr = StreamingManager()
        s1 = mgr.create_stream(tool_name="search")
        s2 = mgr.create_stream(tool_name="fetch")
        s1.start()
        s2.start()
        s1.complete()
        s2.fail()
        removed = mgr.cleanup_completed()
        assert removed == 2
        assert mgr.get_stats()["total_streams"] == 0

    def test_get_stats(self):
        mgr = StreamingManager()
        s1 = mgr.create_stream(tool_name="search")
        s1.start()
        stats = mgr.get_stats()
        assert stats["total_streams"] == 1
        assert stats["active_streams"] == 1
        assert "active" in stats["state_breakdown"]
