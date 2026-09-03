"""Explanation Engine — converts plane outputs to user-friendly explanations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExplanationRequest:
    """A request for explanation."""
    query: str
    result: dict[str, Any] = field(default_factory=dict)
    quality_scores: dict[str, float] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplanationResponse:
    """Response from the explainer."""
    summary: str
    detail: str
    confidence_label: str  # High / Medium / Low
    confidence_score: float  # 0.0 - 1.0
    format: str  # markdown / html / plaintext
    citations: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)


class Explainer:
    """Explains reasoning in user-friendly form."""

    def __init__(self):
        self._confidence_threshold_high = 0.8
        self._confidence_threshold_medium = 0.5

    async def explain(
        self,
        query: str,
        result: dict[str, Any] | None = None,
        quality_scores: dict[str, float] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExplanationResponse:
        """Generate explanation for a result."""
        result = result or {}
        quality_scores = quality_scores or {}
        context = context or {}

        # Calculate overall confidence
        confidence = self._calculate_confidence(quality_scores, result)
        confidence_label = self._label_confidence(confidence)

        # Build reasoning chain
        reasoning = self._build_reasoning_chain(result, context)

        # Extract citations
        citations = result.get("citations", result.get("sources", []))

        # Find unverified claims
        unverified = self._find_unverified_claims(result)

        # Build summary and detail
        summary = self._build_summary(query, result, confidence_label)
        detail = self._build_detail(query, result, confidence, reasoning, citations)

        return ExplanationResponse(
            summary=summary,
            detail=detail,
            confidence_label=confidence_label,
            confidence_score=confidence,
            format=context.get("format", "markdown"),
            citations=citations,
            unverified_claims=unverified,
            reasoning_chain=reasoning,
        )

    def _calculate_confidence(
        self,
        quality_scores: dict[str, float],
        result: dict[str, Any],
    ) -> float:
        """Calculate overall confidence score."""
        if quality_scores:
            return sum(quality_scores.values()) / len(quality_scores)

        if "confidence" in result:
            return float(result["confidence"])

        return 0.7  # Default

    def _label_confidence(self, score: float) -> str:
        """Convert numeric score to label."""
        if score >= self._confidence_threshold_high:
            return "High"
        elif score >= self._confidence_threshold_medium:
            return "Medium"
        else:
            return "Low"

    def _build_reasoning_chain(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
    ) -> list[str]:
        """Build chain of reasoning steps."""
        chain = []

        if "steps" in result:
            chain.extend(result["steps"])
        elif "reasoning" in result:
            if isinstance(result["reasoning"], list):
                chain.extend(result["reasoning"])
            else:
                chain.append(str(result["reasoning"]))

        if "search_queries" in context:
            chain.append(f"Search queries used: {context['search_queries']}")

        if not chain:
            chain.append("Direct answer from available knowledge")

        return chain

    def _find_unverified_claims(self, result: dict[str, Any]) -> list[str]:
        """Identify claims that haven't been verified."""
        claims = result.get("claims", result.get("assertions", []))
        unverified = []
        for claim in claims:
            if isinstance(claim, dict):
                if not claim.get("verified", True):
                    unverified.append(claim.get("text", str(claim)))
            elif isinstance(claim, str):
                unverified.append(claim)
        return unverified

    def _build_summary(
        self,
        query: str,
        result: dict[str, Any],
        confidence_label: str,
    ) -> str:
        """Build a one-sentence summary."""
        answer = result.get("answer", result.get("result", result.get("summary", "")))
        if answer:
            return f"Answer: {answer} (Confidence: {confidence_label})"
        return f"I found information about '{query}' (Confidence: {confidence_label})"

    def _build_detail(
        self,
        query: str,
        result: dict[str, Any],
        confidence: float,
        reasoning: list[str],
        citations: list[str],
    ) -> str:
        """Build detailed explanation."""
        lines = [
            f"# Explanation for: {query}",
            "",
            f"Overall confidence: {confidence:.0%}",
            "",
        ]

        if reasoning:
            lines.append("## Reasoning")
            for i, step in enumerate(reasoning, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if citations:
            lines.append("## Sources")
            for cite in citations:
                lines.append(f"- {cite}")
            lines.append("")

        return "\n".join(lines)
