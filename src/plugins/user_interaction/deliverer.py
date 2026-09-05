"""Result Deliverer — formats and delivers results across multiple channels."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .explainer import ExplanationResponse


class Channel(str, Enum):
    CHAT = "chat"
    EMAIL = "email"
    REPORT = "report"
    JSON = "json"
    STREAM = "stream"


@dataclass
class DeliveryRequest:
    """A request to deliver results."""
    query: str
    result: dict[str, Any] = field(default_factory=dict)
    explanation: ExplanationResponse | None = None
    channel: Channel = Channel.CHAT


@dataclass
class DeliveryResponse:
    """Response from the deliverer."""
    content: str
    channel: Channel
    executive_summary: str = ""
    detailed_breakdown: str = ""
    citations: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    format: str = "markdown"


class ResultDeliverer:
    """Formats and delivers results across multiple channels."""

    async def deliver(
        self,
        query: str,
        result: dict[str, Any] | None = None,
        explanation: ExplanationResponse | None = None,
        channel: Channel = Channel.CHAT,
    ) -> DeliveryResponse:
        """Deliver results through the specified channel."""
        result = result or {}

        # Build content based on channel
        if channel == Channel.CHAT:
            content = self._format_chat(query, result, explanation)
        elif channel == Channel.EMAIL:
            content = self._format_email(query, result, explanation)
        elif channel == Channel.REPORT:
            content = self._format_report(query, result, explanation)
        elif channel == Channel.JSON:
            content = self._format_json(query, result, explanation)
        elif channel == Channel.STREAM:
            content = self._format_stream(query, result, explanation)
        else:
            content = self._format_chat(query, result, explanation)

        # Build executive summary
        summary = self._build_executive_summary(query, result, explanation)

        return DeliveryResponse(
            content=content,
            channel=channel,
            executive_summary=summary,
            detailed_breakdown=explanation.detail if explanation else "",
            citations=explanation.citations if explanation else [],
            unverified_claims=explanation.unverified_claims if explanation else [],
            format=channel.value,
        )

    def _format_chat(
        self,
        query: str,
        result: dict[str, Any],
        explanation: ExplanationResponse | None,
    ) -> str:
        """Format for chat/conversational output."""
        lines = []

        if explanation:
            lines.append(explanation.summary)
            lines.append("")

        # Main content
        answer = result.get("answer", result.get("result", str(result)))
        if answer and not explanation:
            lines.append(str(answer))

        # Confidence indicator
        if explanation and explanation.confidence_label:
            emoji = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(
                explanation.confidence_label, "⚪"
            )
            lines.append(f"{emoji} Confidence: {explanation.confidence_label}")

        # Citations
        if explanation and explanation.citations:
            lines.append("")
            lines.append("Sources:")
            for cite in explanation.citations[:5]:
                lines.append(f"  - {cite}")

        # Unverified claims
        if explanation and explanation.unverified_claims:
            lines.append("")
            lines.append("⚠️ Unverified claims:")
            for claim in explanation.unverified_claims:
                lines.append(f"  - {claim}")

        return "\n".join(lines)

    def _format_email(
        self,
        query: str,
        result: dict[str, Any],
        explanation: ExplanationResponse | None,
    ) -> str:
        """Format for email output."""
        lines = [
            f"Subject: Research Results — {query}",
            "",
            "Executive Summary:",
            "",
        ]

        if explanation:
            lines.append(explanation.summary)
            lines.append("")

            if explanation.unverified_claims:
                lines.append("⚠️ Some claims could not be fully verified.")
                lines.append("")

            if explanation.citations:
                lines.append("Sources:")
                for cite in explanation.citations:
                    lines.append(f"  • {cite}")
                lines.append("")

        return "\n".join(lines)

    def _format_report(
        self,
        query: str,
        result: dict[str, Any],
        explanation: ExplanationResponse | None,
    ) -> str:
        """Format for full report output."""
        lines = [
            f"# Research Report: {query}",
            "",
            "## Executive Summary",
            "",
        ]

        if explanation:
            lines.append(explanation.summary)
            lines.append("")
            lines.append("## Detailed Findings")
            lines.append("")
            lines.append(explanation.detail)

            if explanation.reasoning_chain:
                lines.append("")
                lines.append("## Reasoning")
                for i, step in enumerate(explanation.reasoning_chain, 1):
                    lines.append(f"{i}. {step}")

            if explanation.citations:
                lines.append("")
                lines.append("## References")
                for cite in explanation.citations:
                    lines.append(f"- {cite}")

            if explanation.unverified_claims:
                lines.append("")
                lines.append("## Unverified Claims")
                for claim in explanation.unverified_claims:
                    lines.append(f"- ⚠️ {claim}")

        return "\n".join(lines)

    def _format_json(
        self,
        query: str,
        result: dict[str, Any],
        explanation: ExplanationResponse | None,
    ) -> str:
        """Format as JSON."""
        import json
        data = {
            "query": query,
            "result": result,
            "explanation": None,
        }
        if explanation:
            data["explanation"] = {
                "summary": explanation.summary,
                "confidence": explanation.confidence_label,
                "citations": explanation.citations,
                "unverified_claims": explanation.unverified_claims,
            }
        return json.dumps(data, indent=2)

    def _format_stream(
        self,
        query: str,
        result: dict[str, Any],
        explanation: ExplanationResponse | None,
    ) -> str:
        """Format for streaming output."""
        lines = []
        if explanation:
            lines.append(explanation.summary)
            lines.append("")
            if explanation.unverified_claims:
                lines.append("⚠️ Some claims could not be verified.")
        return "\n".join(lines)

    def _build_executive_summary(
        self,
        query: str,
        result: dict[str, Any],
        explanation: ExplanationResponse | None,
    ) -> str:
        """Build executive summary."""
        if explanation:
            return explanation.summary
        return f"Research complete for: {query}"
