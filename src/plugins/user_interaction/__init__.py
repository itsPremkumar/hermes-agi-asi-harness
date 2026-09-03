"""User Interaction & Explanation Plane — Plane 22.

The last plane in the pipeline. Receives output from all other planes,
formats it for users, asks clarifying questions when ambiguous, and
delivers results across multiple channels.

Integration:
  - Plane 12 (Action Selection) delivers results through this plane
  - Plane 22 receives quality scores from Plane 13 (Verification)
  - Plane 22 formats output from Plane 4 (Deep Research)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.runtime.plugin_base import PluginBase, PluginManifest, PluginState

from .clarifier import Clarifier, ClarificationRequest, ClarificationResponse
from .deliverer import Channel, DeliveryRequest, DeliveryResponse, ResultDeliverer
from .explainer import ExplanationRequest, ExplanationResponse, Explainer


class UserInteractionPlugin(PluginBase):
    """Plugin: User Interaction & Explanation Plane (Plane 22)."""

    def __init__(self, manifest: PluginManifest, kernel: Any = None):
        super().__init__(manifest, kernel)
        self._clarifier: Clarifier | None = None
        self._explainer: Explainer | None = None
        self._deliverer: ResultDeliverer | None = None
        self._session_history: list[dict[str, Any]] = []

    async def load(self) -> bool:
        self._clarifier = Clarifier()
        self._explainer = Explainer()
        self._deliverer = ResultDeliverer()
        self.state = PluginState.LOADED
        return True

    async def start(self) -> bool:
        if not self._clarifier:
            await self.load()
        self.state = PluginState.RUNNING
        return True

    async def pause(self) -> bool:
        self.state = PluginState.PAUSED
        return True

    async def resume(self) -> bool:
        self.state = PluginState.RUNNING
        return True

    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True

    async def unload(self) -> bool:
        self._clarifier = None
        self._explainer = None
        self._deliverer = None
        self.state = PluginState.UNLOADED
        return True

    async def health(self) -> dict[str, Any]:
        base = await super().health()
        base["clarifier_ready"] = self._clarifier is not None
        base["explainer_ready"] = self._explainer is not None
        base["deliverer_ready"] = self._deliverer is not None
        base["session_count"] = len(self._session_history)
        return base

    async def process(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        quality_scores: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Process a user query through the full pipeline."""
        context = context or {}
        quality_scores = quality_scores or {}

        # Step 1: Clarify if needed
        clarification = None
        if self._clarifier:
            clarification = await self._clarifier.clarify(query, context)

        # Step 2: Get result from upstream planes
        result = context.get("result", {})

        # Step 3: Explain
        explanation = None
        if self._explainer:
            explanation = await self._explainer.explain(
                query=query,
                result=result,
                quality_scores=quality_scores,
                context=context,
            )

        # Step 4: Deliver
        delivery = None
        if self._deliverer:
            delivery = await self._deliverer.deliver(
                query=query,
                result=result,
                explanation=explanation,
                channel=context.get("channel", Channel.CHAT),
            )

        # Record session
        self._session_history.append({
            "query": query,
            "clarification": clarification,
            "explanation": explanation,
            "delivery": delivery,
        })

        return {
            "query": query,
            "needs_clarification": clarification is not None and not clarification.is_resolved,
            "clarification": clarification,
            "explanation": explanation,
            "delivery": delivery,
            "quality_scores": quality_scores,
        }


__all__ = [
    "UserInteractionPlugin",
    "Clarifier",
    "ClarificationRequest",
    "ClarificationResponse",
    "Explainer",
    "ExplanationRequest",
    "ExplanationResponse",
    "ResultDeliverer",
    "DeliveryRequest",
    "DeliveryResponse",
    "Channel",
]
