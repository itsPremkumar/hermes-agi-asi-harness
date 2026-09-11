"""
Tests for FeedbackLoop module.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.harness.improvement.feedback import (
    FeedbackCategory,
    FeedbackItem,
    FeedbackLoop,
    FeedbackPriority,
    FeedbackSummary,
)


@pytest.fixture
def loop() -> FeedbackLoop:
    return FeedbackLoop()


@pytest.fixture
def populated_loop() -> FeedbackLoop:
    loop = FeedbackLoop()
    loop.submit_feedback("agent1", FeedbackCategory.QUALITY, "Code is clean", FeedbackPriority.LOW)
    loop.submit_feedback("agent1", FeedbackCategory.BUG, "Found a bug", FeedbackPriority.HIGH)
    loop.submit_feedback("agent2", FeedbackCategory.PERFORMANCE, "Too slow", FeedbackPriority.CRITICAL)
    loop.submit_feedback("agent2", FeedbackCategory.SUGGESTION, "Add caching", FeedbackPriority.MEDIUM)
    loop.submit_feedback("agent3", FeedbackCategory.RELIABILITY, "Flaky tests", FeedbackPriority.HIGH)
    return loop


class TestFeedbackItem:
    def test_item_creation(self) -> None:
        item = FeedbackItem(
            agent_name="agent1",
            category=FeedbackCategory.QUALITY,
            message="Good work",
        )
        assert item.agent_name == "agent1"
        assert item.resolved is False

    def test_resolve(self) -> None:
        item = FeedbackItem(
            agent_name="agent1",
            category=FeedbackCategory.BUG,
            message="Bug found",
        )
        item.resolve("Fixed in commit abc")
        assert item.resolved is True
        assert item.resolution == "Fixed in commit abc"
        assert item.resolution_time is not None

    def test_age_hours(self) -> None:
        item = FeedbackItem(
            agent_name="agent1",
            category=FeedbackCategory.QUALITY,
            message="Test",
        )
        assert item.age_hours < 0.001


class TestFeedbackLoop:
    def test_submit_feedback(self, loop: FeedbackLoop) -> None:
        item = loop.submit_feedback("agent1", FeedbackCategory.QUALITY, "Good")
        assert item.agent_name == "agent1"
        assert item.category == FeedbackCategory.QUALITY
        assert item.feedback_id != ""

    def test_submit_feedback_string_category(self, loop: FeedbackLoop) -> None:
        item = loop.submit_feedback("agent1", "quality", "Good")
        assert item.category == FeedbackCategory.QUALITY

    def test_submit_feedback_string_priority(self, loop: FeedbackLoop) -> None:
        item = loop.submit_feedback("agent1", "quality", "Good", "high")
        assert item.priority == FeedbackPriority.HIGH

    def test_resolve_feedback(self, loop: FeedbackLoop) -> None:
        item = loop.submit_feedback("agent1", "bug", "Bug found")
        resolved = loop.resolve_feedback(item.feedback_id, "Fixed")
        assert resolved is not None
        assert resolved.resolved is True

    def test_resolve_feedback_not_found(self, loop: FeedbackLoop) -> None:
        resolved = loop.resolve_feedback("nonexistent", "Fixed")
        assert resolved is None

    def test_get_by_agent(self, populated_loop: FeedbackLoop) -> None:
        items = populated_loop.get_by_agent("agent1")
        assert len(items) == 2

    def test_get_by_category(self, populated_loop: FeedbackLoop) -> None:
        items = populated_loop.get_by_category(FeedbackCategory.BUG)
        assert len(items) == 1

    def test_get_by_category_string(self, populated_loop: FeedbackLoop) -> None:
        items = populated_loop.get_by_category("bug")
        assert len(items) == 1

    def test_get_by_priority(self, populated_loop: FeedbackLoop) -> None:
        items = populated_loop.get_by_priority(FeedbackPriority.HIGH)
        assert len(items) == 2

    def test_get_critical_unresolved(self, populated_loop: FeedbackLoop) -> None:
        critical = populated_loop.get_critical_unresolved()
        assert len(critical) == 1
        assert critical[0].priority == FeedbackPriority.CRITICAL

    def test_get_stale_feedback(self, loop: FeedbackLoop) -> None:
        item = loop.submit_feedback("agent1", "bug", "Old bug")
        # Manually set timestamp to old date
        item.timestamp = datetime.utcnow() - timedelta(hours=72)
        stale = loop.get_stale_feedback(max_age_hours=48)
        assert len(stale) == 1

    def test_subscribe(self, loop: FeedbackLoop) -> None:
        loop.subscribe("agent1", FeedbackCategory.BUG)
        subs = loop.get_subscribers(FeedbackCategory.BUG)
        assert "agent1" in subs

    def test_subscribe_string_category(self, loop: FeedbackLoop) -> None:
        loop.subscribe("agent1", "bug")
        subs = loop.get_subscribers("bug")
        assert "agent1" in subs

    def test_generate_summary(self, populated_loop: FeedbackLoop) -> None:
        summary = populated_loop.generate_summary()
        assert summary.total_items == 5
        assert summary.unresolved_items == 5
        assert summary.resolved_items == 0
        assert FeedbackCategory.QUALITY.value in summary.by_category
        assert "agent1" in summary.by_agent

    def test_generate_summary_with_resolved(self, populated_loop: FeedbackLoop) -> None:
        items = populated_loop.get_by_agent("agent1")
        items[0].resolve("Done")
        summary = populated_loop.generate_summary()
        assert summary.resolved_items == 1
        assert summary.avg_resolution_hours is not None

    def test_get_actionable_items(self, populated_loop: FeedbackLoop) -> None:
        items = populated_loop.get_actionable_items()
        assert len(items) == 5
        # Critical should be first
        assert items[0]["priority"] == FeedbackPriority.CRITICAL.value

    def test_get_agent_sentiment(self, populated_loop: FeedbackLoop) -> None:
        sentiment = populated_loop.get_agent_sentiment("agent1")
        assert sentiment["total"] == 2
        assert sentiment["sentiment"] in ("positive", "negative", "neutral")

    def test_get_agent_sentiment_empty(self, loop: FeedbackLoop) -> None:
        sentiment = loop.get_agent_sentiment("nonexistent")
        assert sentiment["total"] == 0

    def test_export_feedback(self, populated_loop: FeedbackLoop) -> None:
        exported = populated_loop.export_feedback()
        assert len(exported) == 5
        assert "id" in exported[0]
        assert "agent" in exported[0]
        assert "category" in exported[0]

    def test_unresolved_feedback_property(self, populated_loop: FeedbackLoop) -> None:
        items = populated_loop.get_by_agent("agent1")
        items[0].resolve("Done")
        assert len(populated_loop.unresolved_feedback) == 4
        assert len(populated_loop.resolved_feedback) == 1

    def test_all_feedback_property(self, populated_loop: FeedbackLoop) -> None:
        assert len(populated_loop.all_feedback) == 5

    def test_feedback_id_unique(self, loop: FeedbackLoop) -> None:
        item1 = loop.submit_feedback("a1", "quality", "msg1")
        item2 = loop.submit_feedback("a1", "quality", "msg2")
        assert item1.feedback_id != item2.feedback_id
