"""Recovery Engine for ASI Cognitive Architecture.

Provides checkpoint/resume capability, partial result delivery,
graceful degradation chain, and escalation procedures.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from . import (
    CircuitBreakerPlugin,
    CircuitState,
    get_fallbacks,
)

logger = logging.getLogger("hermes_recovery")


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    result: Any = None
    used_fallback: bool = False
    fallback_name: str = ""
    partial: bool = False
    missing: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class Checkpoint:
    """Saved state for recovery."""
    task_id: str
    plane_name: str
    state: dict[str, Any]
    timestamp: float
    completed_planes: list[str] = field(default_factory=list)
    remaining_planes: list[str] = field(default_factory=list)
    partial_results: dict[str, Any] = field(default_factory=dict)


class RecoveryEngine:
    """Handles failure recovery and graceful degradation."""

    def __init__(self, circuit_breaker: CircuitBreakerPlugin):
        self._cb = circuit_breaker
        self._checkpoints: dict[str, Checkpoint] = {}
        self._degradation_chain: dict[str, list[str]] = {
            # If primary plane fails, try these in order
            "meta_reasoning": ["default_strategy"],
            "deep_research": ["cached_knowledge", "skip_research"],
            "search": ["cached_results", "local_knowledge", "ask_user"],
            "multi_agent": ["single_agent", "sequential_execution"],
            "tree_of_thoughts": ["beam_search", "greedy_selection"],
            "verification": ["skip_verification", "self_check_only"],
            "avo": ["random_search", "single_candidate"],
            "memory": ["compress_oldest", "skip_storage"],
        }

    def save_checkpoint(
        self,
        task_id: str,
        plane_name: str,
        state: dict[str, Any],
        completed_planes: list[str] | None = None,
        remaining_planes: list[str] | None = None,
        partial_results: dict[str, Any] | None = None,
    ) -> None:
        """Save a checkpoint for later recovery."""
        self._checkpoints[task_id] = Checkpoint(
            task_id=task_id,
            plane_name=plane_name,
            state=state,
            timestamp=time.time(),
            completed_planes=completed_planes or [],
            remaining_planes=remaining_planes or [],
            partial_results=partial_results or {},
        )
        logger.info(f"Checkpoint saved: {task_id} at plane {plane_name}")

    def load_checkpoint(self, task_id: str) -> Checkpoint | None:
        """Load a checkpoint for recovery."""
        cp = self._checkpoints.get(task_id)
        if cp:
            logger.info(f"Checkpoint loaded: {task_id}")
        return cp

    async def try_recover(
        self,
        task_id: str,
        plane_name: str,
        operation: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> RecoveryResult:
        """
        Attempt to recover from a failure using checkpoint + fallback.

        Strategy:
        1. Try to resume from last checkpoint
        2. Try the operation with circuit breaker
        3. Try each fallback in the chain
        4. Return partial results if all else fails
        """
        # Step 1: Load checkpoint if available
        checkpoint = self.load_checkpoint(task_id)

        # Step 2: Try the operation
        try:
            result, used_fallback = await self._cb.call_plane(
                plane_name,
                operation,
                *args,
                **kwargs,
            )
            if result is not None:
                if used_fallback:
                    return RecoveryResult(
                        success=True,
                        result=result,
                        used_fallback=True,
                        fallback_name="circuit_breaker_fallback",
                    )
                return RecoveryResult(success=True, result=result)
        except Exception as e:
            logger.warning(f"Operation failed for {plane_name}: {e}")

        # Step 3: Try fallback chain
        fallbacks = get_fallbacks(plane_name)
        for i, fallback_fn in enumerate(fallbacks):
            try:
                result = await fallback_fn(*args, **kwargs)
                return RecoveryResult(
                    success=True,
                    result=result,
                    used_fallback=True,
                    fallback_name=f"{plane_name}_fallback_{i}",
                )
            except Exception as e:
                logger.warning(f"Fallback {i} for {plane_name} failed: {e}")

        # Step 4: Return partial results with checkpoint
        if checkpoint:
            return RecoveryResult(
                success=False,
                result=checkpoint.partial_results,
                partial=True,
                missing=checkpoint.remaining_planes,
                note=f"Recovered from checkpoint. Missing: {checkpoint.remaining_planes}",
            )

        return RecoveryResult(
            success=False,
            note=f"All recovery options exhausted for {plane_name}",
        )

    async def graceful_degrade(
        self,
        task_id: str,
        failed_plane: str,
        remaining_planes: list[str],
    ) -> RecoveryResult:
        """
        Gracefully degrade by skipping the failed plane and continuing
        with remaining planes using available data.
        """
        logger.warning(f"Graceful degradation: skipping {failed_plane}")

        # Check if we have partial results from the failed plane
        checkpoint = self.load_checkpoint(task_id)
        partial = checkpoint.partial_results if checkpoint else {}

        # Determine what we can still do
        still_available = [
            p for p in remaining_planes
            if self._cb.get_plane_health(p).get("circuit_state") != CircuitState.OPEN.value
        ]

        missing = [p for p in remaining_planes if p not in still_available]

        return RecoveryResult(
            success=len(still_available) > 0,
            result={
                "degraded": True,
                "skipped_plane": failed_plane,
                "available_planes": still_available,
                "partial_results": partial,
            },
            partial=True,
            missing=missing,
            note=f"Degraded: skipped {failed_plane}, continuing with {len(still_available)} planes",
        )

    def get_degradation_chain(self, plane_name: str) -> list[str]:
        """Get the degradation chain for a plane."""
        return self._degradation_chain.get(plane_name, [])

    def escalate(
        self,
        plane_name: str,
        error: str,
        severity: str = "warning",
    ) -> dict[str, Any]:
        """
        Generate an escalation record for critical failures.

        Returns escalation dict with all relevant context.
        """
        health = self._cb.get_plane_health(plane_name)
        escalation = {
            "timestamp": time.time(),
            "plane": plane_name,
            "severity": severity,
            "error": error,
            "health_snapshot": health,
            "action_required": severity in ("critical", "error"),
            "recommended_action": self._recommend_action(plane_name, health),
        }

        if severity == "critical":
            logger.critical(f"ESCALATION: {plane_name} - {error}")
        elif severity == "error":
            logger.error(f"ESCALATION: {plane_name} - {error}")
        else:
            logger.warning(f"ESCALATION: {plane_name} - {error}")

        return escalation

    def _recommend_action(self, plane_name: str, health: dict[str, Any]) -> str:
        """Generate a recommendation based on health."""
        if health["circuit_state"] == CircuitState.OPEN.value:
            if health["errors_per_minute"] > 10:
                return f"Plane {plane_name}: Disable manually, investigate root cause"
            return f"Plane {plane_name}: Wait for auto-recovery or use fallback"
        elif health["error_rate"] > 0.5:
            return f"Plane {plane_name}: Check logs, consider fallback"
        elif health.get("p95_latency_ms", 0) > 10000:
            return f"Plane {plane_name}: Slow responses, consider timeout increase"
        return f"Plane {plane_name}: Monitor, no immediate action"

    def get_recovery_options(self, plane_name: str) -> dict[str, Any]:
        """Get available recovery options for a plane."""
        health = self._cb.get_plane_health(plane_name)
        return {
            "plane": plane_name,
            "circuit_state": health["circuit_state"],
            "available_fallbacks": get_fallbacks(plane_name),
            "degradation_chain": self.get_degradation_chain(plane_name),
            "can_retry": health["circuit_state"] != CircuitState.OPEN.value,
            "can_checkpoint": plane_name in self._checkpoints,
        }
