"""
FeedbackLoop — Structured feedback collection from all agents.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class FeedbackCategory(str, Enum):
    QUALITY = "quality"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    RELIABILITY = "reliability"
    SUGGESTION = "suggestion"
    BUG = "bug"


class FeedbackPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FeedbackItem:
    """A single piece of feedback from an agent."""

    agent_name: str
    category: FeedbackCategory
    message: str
    priority: FeedbackPriority = FeedbackPriority.MEDIUM
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution: str = ""
    resolution_time: datetime | None = None
    feedback_id: str = ""

    def resolve(self, resolution: str) -> None:
        """Mark this feedback as resolved."""
        self.resolved = True
        self.resolution = resolution
        self.resolution_time = datetime.utcnow()

    @property
    def age_hours(self) -> float:
        """Age of this feedback in hours."""
        delta = datetime.utcnow() - self.timestamp
        return delta.total_seconds() / 3600.0


@dataclass
class FeedbackSummary:
    """Summary of feedback across all agents."""

    total_items: int = 0
    resolved_items: int = 0
    unresolved_items: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    by_priority: dict[str, int] = field(default_factory=dict)
    by_agent: dict[str, int] = field(default_factory=dict)
    avg_resolution_hours: float = 0.0
    resolution_rate: float = 0.0


class FeedbackLoop:
    """Collects, organizes, and manages structured feedback from all agents."""

    def __init__(self) -> None:
        self._feedback_items: list[FeedbackItem] = []
        self._subscribers: dict[str, list[str]] = {}  # category -> list of agent names
        self._id_counter = 0

    @property
    def all_feedback(self) -> list[FeedbackItem]:
        return list(self._feedback_items)

    @property
    def unresolved_feedback(self) -> list[FeedbackItem]:
        return [f for f in self._feedback_items if not f.resolved]

    @property
    def resolved_feedback(self) -> list[FeedbackItem]:
        return [f for f in self._feedback_items if f.resolved]

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"fb-{self._id_counter:04d}"

    def submit_feedback(
        self,
        agent_name: str,
        category: FeedbackCategory | str,
        message: str,
        priority: FeedbackPriority | str = FeedbackPriority.MEDIUM,
        context: dict[str, Any] | None = None,
    ) -> FeedbackItem:
        """Submit a new feedback item."""
        if isinstance(category, str):
            category = FeedbackCategory(category)
        if isinstance(priority, str):
            priority = FeedbackPriority(priority)

        item = FeedbackItem(
            agent_name=agent_name,
            category=category,
            message=message,
            priority=priority,
            context=context or {},
            feedback_id=self._next_id(),
        )

        self._feedback_items.append(item)
        return item

    def resolve_feedback(self, feedback_id: str, resolution: str) -> FeedbackItem | None:
        """Resolve a feedback item by ID."""
        for item in self._feedback_items:
            if item.feedback_id == feedback_id:
                item.resolve(resolution)
                return item
        return None

    def get_by_agent(self, agent_name: str) -> list[FeedbackItem]:
        """Get all feedback from a specific agent."""
        return [f for f in self._feedback_items if f.agent_name == agent_name]

    def get_by_category(self, category: FeedbackCategory | str) -> list[FeedbackItem]:
        """Get all feedback in a specific category."""
        if isinstance(category, str):
            category = FeedbackCategory(category)
        return [f for f in self._feedback_items if f.category == category]

    def get_by_priority(self, priority: FeedbackPriority | str) -> list[FeedbackItem]:
        """Get all feedback with a specific priority."""
        if isinstance(priority, str):
            priority = FeedbackPriority(priority)
        return [f for f in self._feedback_items if f.priority == priority]

    def get_critical_unresolved(self) -> list[FeedbackItem]:
        """Get all unresolved critical feedback."""
        return [
            f for f in self._feedback_items
            if not f.resolved and f.priority == FeedbackPriority.CRITICAL
        ]

    def get_stale_feedback(self, max_age_hours: float = 48.0) -> list[FeedbackItem]:
        """Get unresolved feedback older than the threshold."""
        return [
            f for f in self._feedback_items
            if not f.resolved and f.age_hours > max_age_hours
        ]

    def subscribe(self, agent_name: str, category: FeedbackCategory | str) -> None:
        """Subscribe an agent to notifications for a feedback category."""
        if isinstance(category, str):
            category = FeedbackCategory(category)
        cat_val = category.value
        if cat_val not in self._subscribers:
            self._subscribers[cat_val] = []
        if agent_name not in self._subscribers[cat_val]:
            self._subscribers[cat_val].append(agent_name)

    def get_subscribers(self, category: FeedbackCategory | str) -> list[str]:
        """Get all agents subscribed to a category."""
        if isinstance(category, str):
            category = FeedbackCategory(category)
        return list(self._subscribers.get(category.value, []))

    def generate_summary(self) -> FeedbackSummary:
        """Generate a summary of all feedback."""
        summary = FeedbackSummary()
        summary.total_items = len(self._feedback_items)
        summary.resolved_items = sum(1 for f in self._feedback_items if f.resolved)
        summary.unresolved_items = summary.total_items - summary.resolved_items

        for item in self._feedback_items:
            cat = item.category.value
            pri = item.priority.value
            summary.by_category[cat] = summary.by_category.get(cat, 0) + 1
            summary.by_priority[pri] = summary.by_priority.get(pri, 0) + 1
            summary.by_agent[item.agent_name] = summary.by_agent.get(item.agent_name, 0) + 1

        resolved_with_time = [
            f for f in self._feedback_items
            if f.resolved and f.resolution_time
        ]
        if resolved_with_time:
            resolution_hours = [
                (f.resolution_time - f.timestamp).total_seconds() / 3600.0
                for f in resolved_with_time
            ]
            summary.avg_resolution_hours = statistics.mean(resolution_hours)

        summary.resolution_rate = (
            summary.resolved_items / summary.total_items if summary.total_items > 0 else 0.0
        )

        return summary

    def get_actionable_items(self) -> list[dict[str, Any]]:
        """Get feedback items that require action, sorted by priority."""
        priority_order = {
            FeedbackPriority.CRITICAL: 0,
            FeedbackPriority.HIGH: 1,
            FeedbackPriority.MEDIUM: 2,
            FeedbackPriority.LOW: 3,
        }

        unresolved = [f for f in self._feedback_items if not f.resolved]
        unresolved.sort(key=lambda f: (priority_order.get(f.priority, 4), -f.age_hours))

        return [
            {
                "id": f.feedback_id,
                "agent": f.agent_name,
                "category": f.category.value,
                "priority": f.priority.value,
                "message": f.message,
                "age_hours": f.age_hours,
                "context": f.context,
            }
            for f in unresolved
        ]

    def get_agent_sentiment(self, agent_name: str) -> dict[str, Any]:
        """Analyze the sentiment of feedback from a specific agent."""
        items = self.get_by_agent(agent_name)
        if not items:
            return {"agent": agent_name, "total": 0, "sentiment": "neutral"}

        # Simple heuristic: count bug/critical as negative, suggestion as positive
        negative = sum(1 for f in items if f.category in (FeedbackCategory.BUG, FeedbackCategory.RELIABILITY))
        positive = sum(1 for f in items if f.category == FeedbackCategory.SUGGESTION)
        neutral = len(items) - negative - positive

        if negative > positive and negative > neutral:
            sentiment = "negative"
        elif positive > negative and positive > neutral:
            sentiment = "positive"
        else:
            sentiment = "neutral"

        return {
            "agent": agent_name,
            "total": len(items),
            "sentiment": sentiment,
            "negative": negative,
            "positive": positive,
            "neutral": neutral,
        }

    def export_feedback(self, format: str = "dict") -> list[dict[str, Any]]:
        """Export all feedback in the specified format."""
        if format == "dict":
            return [
                {
                    "id": f.feedback_id,
                    "agent": f.agent_name,
                    "category": f.category.value,
                    "priority": f.priority.value,
                    "message": f.message,
                    "timestamp": f.timestamp.isoformat(),
                    "resolved": f.resolved,
                    "resolution": f.resolution,
                    "context": f.context,
                }
                for f in self._feedback_items
            ]
        return []
