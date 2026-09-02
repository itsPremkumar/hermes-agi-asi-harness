"""Clarification Engine — detects ambiguous queries and asks focused questions."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClarificationRequest:
    """A request for clarification."""
    query: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClarificationResponse:
    """Response from the clarifier."""
    is_resolved: bool
    question: str | None = None
    priority: int = 0  # 1=high, 2=medium, 3=low
    options: list[str] = field(default_factory=list)
    category: str = ""  # scope, detail, format, urgency, audience


class Clarifier:
    """Detects ambiguity and generates clarifying questions."""

    # Patterns that indicate ambiguity
    AMBIGUITY_PATTERNS = {
        "scope": [
            r"\b(all|every|each|any)\b",
            r"\b(some|few|several|many)\b",
            r"\b(best|top|most|least)\b",
        ],
        "detail": [
            r"\b(detail|explain|describe|what|how|why)\b",
            r"\b(brief|summary|overview|deep|thorough)\b",
        ],
        "format": [
            r"\b(list|table|chart|graph|report|doc|pdf)\b",
            r"\b(json|csv|xml|yaml|markdown)\b",
        ],
        "urgency": [
            r"\b(soon|quickly|fast|asap|now)\b",
            r"\b(later|eventually|whenever)\b",
        ],
        "audience": [
            r"\b(beginner|expert|technical|non-technical|child|adult)\b",
            r"\b(me|team|boss|client|customer|user)\b",
        ],
    }

    # Question templates per category
    QUESTIONS = {
        "scope": "What scope should this cover — everything or a specific subset?",
        "detail": "How much detail do you need — brief overview or deep analysis?",
        "format": "What format would be most useful — list, table, report, or raw data?",
        "urgency": "When do you need this — immediately or is there flexibility?",
        "audience": "Who is the audience — technical experts or general readers?",
    }

    # Priority by category
    PRIORITY = {
        "scope": 1,
        "detail": 2,
        "format": 3,
        "urgency": 2,
        "audience": 3,
    }

    async def clarify(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> ClarificationResponse:
        """Analyze query and generate clarifying question if ambiguous."""
        context = context or {}
        query_lower = query.lower()

        # Check each ambiguity category
        detected_categories: list[tuple[str, int]] = []
        for category, patterns in self.AMBIGUITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    priority = self.PRIORITY.get(category, 3)
                    detected_categories.append((category, priority))
                    break

        # Sort by priority (lower = more important)
        detected_categories.sort(key=lambda x: x[1])

        if not detected_categories:
            return ClarificationResponse(is_resolved=True)

        # Ask the highest-priority question
        top_category = detected_categories[0][0]
        top_priority = detected_categories[0][1]

        return ClarificationResponse(
            is_resolved=False,
            question=self.QUESTIONS.get(top_category, "Could you provide more details?"),
            priority=top_priority,
            category=top_category,
            options=self._generate_options(top_category),
        )

    def _generate_options(self, category: str) -> list[str]:
        """Generate options for a given category."""
        options_map = {
            "scope": ["Everything", "Specific subset", "Just the top items"],
            "detail": ["Brief overview", "Moderate depth", "Deep analysis"],
            "format": ["Markdown text", "Structured list", "Table", "Full report"],
            "urgency": ["Immediately (fastest)", "Balanced", "Thorough (slower)"],
            "audience": ["Technical experts", "General readers", "Mixed audience"],
        }
        return options_map.get(category, [])

    def prioritize_questions(self, questions: list[ClarificationResponse]) -> list[ClarificationResponse]:
        """Sort questions by priority (high to low)."""
        return sorted(questions, key=lambda q: q.priority)

    def should_ask_question(
        self,
        query: str,
        previous_questions: list[str],
        max_questions: int = 3,
    ) -> bool:
        """Determine if we should ask another question."""
        if len(previous_questions) >= max_questions:
            return False
        if len(query.strip()) < 10:
            return True
        return False
