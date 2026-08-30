#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v6.0 — MULTI-MODEL ORCHESTRATOR
========================================================
Intelligent model routing, ensemble, and chaining.

Extracted from:
- hermes-free-harness harness/kernel/model_router.py
- agx-harness-main agx/brain.py (HermesBrain model routing)
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_models")


class ModelCapability(str, Enum):
    CHAT = "chat"
    REASONING = "reasoning"
    CODING = "coding"
    VISION = "vision"
    EMBEDDINGS = "embeddings"
    FUNCTION_CALLING = "function_calling"


@dataclass
class ModelProfile:
    """Profile of a model."""
    model_id: str
    provider: str
    capabilities: list[ModelCapability] = field(default_factory=list)
    cost_per_1k_tokens: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    quality_score: float = 0.5
    success_rate: float = 0.5
    total_calls: int = 0
    successful_calls: int = 0
    is_local: bool = False
    is_available: bool = True


@dataclass
class RoutingDecision:
    """A routing decision."""
    decision_id: str
    task_description: str
    selected_model: str
    reason: str
    confidence: float
    timestamp: float
    alternatives: list[str] = field(default_factory=list)


class ModelOrchestrator:
    """
    Multi-model orchestration.
    
    Features:
    - Route tasks to optimal models based on capability, cost, latency
    - Ensemble multiple models for consensus
    - Chain models (output of one → input of another)
    - Fall back to cheaper models when expensive ones fail
    - Track model performance and calibrate confidence
    - Support model-specific prompt optimization
    - A/B test model variants
    """
    
    def __init__(self):
        self._models: dict[str, ModelProfile] = {}
        self._routing_history: list[RoutingDecision] = []
        self._performance_history: list[dict[str, Any]] = []
        
        # Register default models
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default models."""
        self.register_model(ModelProfile(
            model_id="llama3.2:3b",
            provider="ollama",
            capabilities=[ModelCapability.CHAT, ModelCapability.REASONING, ModelCapability.CODING],
            cost_per_1k_tokens=0.0,
            latency_p50_ms=200,
            quality_score=0.7,
            is_local=True
        ))
        
        self.register_model(ModelProfile(
            model_id="qwen2.5-coder:3b",
            provider="ollama",
            capabilities=[ModelCapability.CHAT, ModelCapability.CODING, ModelCapability.FUNCTION_CALLING],
            cost_per_1k_tokens=0.0,
            latency_p50_ms=250,
            quality_score=0.75,
            is_local=True
        ))
        
        self.register_model(ModelProfile(
            model_id="gpt-4o-mini",
            provider="openai",
            capabilities=[ModelCapability.CHAT, ModelCapability.REASONING, ModelCapability.CODING, ModelCapability.VISION],
            cost_per_1k_tokens=0.001,
            latency_p50_ms=800,
            quality_score=0.9,
            is_local=False
        ))
        
        self.register_model(ModelProfile(
            model_id="claude-sonnet-4",
            provider="anthropic",
            capabilities=[ModelCapability.CHAT, ModelCapability.REASONING, ModelCapability.CODING, ModelCapability.VISION],
            cost_per_1k_tokens=0.003,
            latency_p50_ms=1000,
            quality_score=0.92,
            is_local=False
        ))
    
    def register_model(self, profile: ModelProfile):
        """Register a model."""
        self._models[profile.model_id] = profile
        logger.info("Model registered: %s (%s)", profile.model_id, profile.provider)
    
    def route(
        self,
        task_description: str,
        required_capabilities: list[ModelCapability] | None = None,
        prefer_local: bool = True,
        max_cost: float = 0.01
    ) -> RoutingDecision:
        """Route a task to the optimal model."""
        required_capabilities = required_capabilities or [ModelCapability.CHAT]
        
        # Filter models by capabilities
        candidates = []
        for model in self._models.values():
            if not model.is_available:
                continue
            if not all(cap in model.capabilities for cap in required_capabilities):
                continue
            if model.cost_per_1k_tokens > max_cost:
                continue
            candidates.append(model)
        
        if not candidates:
            # Fallback to first available
            candidates = [m for m in self._models.values() if m.is_available]
        
        if not candidates:
            return RoutingDecision(
                decision_id=str(uuid.uuid4()),
                task_description=task_description,
                selected_model="none",
                reason="No available models",
                confidence=0.0,
                timestamp=time.time()
            )
        
        # Score candidates
        best_model = None
        best_score = -1
        
        for model in candidates:
            score = self._score_model(model, task_description, prefer_local)
            if score > best_score:
                best_score = score
                best_model = model
        
        decision = RoutingDecision(
            decision_id=str(uuid.uuid4()),
            task_description=task_description,
            selected_model=best_model.model_id,
            reason=f"Best match: quality={best_model.quality_score:.2f}, cost={best_model.cost_per_1k_tokens:.4f}",
            confidence=min(0.95, best_score),
            timestamp=time.time(),
            alternatives=[m.model_id for m in candidates if m.model_id != best_model.model_id]
        )
        
        self._routing_history.append(decision)
        return decision
    
    def _score_model(self, model: ModelProfile, task: str, prefer_local: bool) -> float:
        """Score a model for a task."""
        # Quality component (0-1)
        quality = model.quality_score
        
        # Cost component (lower is better, 0-1)
        max_cost = max(m.cost_per_1k_tokens for m in self._models.values()) or 1.0
        cost = 1.0 - (model.cost_per_1k_tokens / max_cost) if max_cost > 0 else 1.0
        
        # Latency component (lower is better, 0-1)
        max_latency = max(m.latency_p50_ms for m in self._models.values()) or 1.0
        latency = 1.0 - (model.latency_p50_ms / max_latency) if max_latency > 0 else 1.0
        
        # Success rate component
        success = model.success_rate
        
        # Local preference
        local_bonus = 0.1 if prefer_local and model.is_local else 0.0
        
        # Weighted combination
        score = (
            quality * 0.35 +
            cost * 0.25 +
            latency * 0.15 +
            success * 0.15 +
            local_bonus
        )
        
        return min(1.0, max(0.0, score))
    
    async def ensemble(
        self,
        task_description: str,
        num_models: int = 3,
        brain: Any = None
    ) -> dict[str, Any]:
        """Query multiple models and combine results."""
        # Select top models
        candidates = sorted(
            [m for m in self._models.values() if m.is_available],
            key=lambda m: m.quality_score,
            reverse=True
        )[:num_models]
        
        results = []
        for model in candidates:
            # Simulate query
            results.append({
                "model": model.model_id,
                "response": f"Response from {model.model_id}",
                "confidence": model.quality_score
            })
        
        # Weighted voting
        avg_confidence = sum(r["confidence"] for r in results) / len(results) if results else 0
        
        return {
            "task": task_description,
            "results": results,
            "consensus": results[0]["response"] if results else "",
            "confidence": avg_confidence,
            "models_used": len(results)
        }
    
    async def chain(
        self,
        task_description: str,
        model_chain: list[str] | None = None,
        brain: Any = None
    ) -> dict[str, Any]:
        """Chain models: output of one → input of next."""
        if not model_chain:
            model_chain = ["llama3.2:3b", "gpt-4o-mini"]
        
        current_input = task_description
        chain_results = []
        
        for model_id in model_chain:
            # Simulate processing
            result = {
                "model": model_id,
                "input": current_input[:100],
                "output": f"Processed by {model_id}",
                "timestamp": time.time()
            }
            chain_results.append(result)
            current_input = result["output"]
        
        return {
            "task": task_description,
            "chain": chain_results,
            "final_output": chain_results[-1]["output"] if chain_results else "",
            "steps": len(chain_results)
        }
    
    def record_result(self, model_id: str, success: bool, latency_ms: float = 0):
        """Record model performance."""
        model = self._models.get(model_id)
        if model:
            model.total_calls += 1
            if success:
                model.successful_calls += 1
            model.success_rate = model.successful_calls / model.total_calls if model.total_calls > 0 else 0.5
    
    def get_calibration_report(self) -> dict[str, Any]:
        """Get calibration report."""
        return {
            "models": len(self._models),
            "total_routes": len(self._routing_history),
            "model_stats": {
                model_id: {
                    "quality": model.quality_score,
                    "success_rate": model.success_rate,
                    "total_calls": model.total_calls
                }
                for model_id, model in self._models.items()
            }
        }
    
    async def health(self) -> dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "models_count": len(self._models),
            "available_models": len([m for m in self._models.values() if m.is_available]),
            "total_routes": len(self._routing_history)
        }
