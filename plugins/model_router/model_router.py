#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v7.0 — MODEL ROUTER
============================================
Free-first model routing with graceful degradation.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProviderKind(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    SPECIALIZED = "specialized"


@dataclass
class ModelSpec:
    name: str
    provider: str
    kind: ProviderKind
    base_url: Optional[str] = None
    cost: str = "free"
    capabilities: List[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


FREE_MODELS: List[ModelSpec] = [
    ModelSpec("llama3.2:3b", "ollama", ProviderKind.LOCAL, "http://localhost:11434/v1", "free", ["chat"]),
    ModelSpec("qwen2.5-coder:3b", "ollama", ProviderKind.LOCAL, "http://localhost:11434/v1", "free", ["coding"]),
    ModelSpec("SmolLM2-1.7B", "hf-local", ProviderKind.LOCAL, None, "free", ["chat"]),
    ModelSpec("bge-small-en-v1.5", "hf-local", ProviderKind.SPECIALIZED, None, "free", ["embeddings"]),
    ModelSpec("all-MiniLM-L6-v2", "hf-local", ProviderKind.SPECIALIZED, None, "free", ["embeddings"]),
]


PAID_MODELS: List[ModelSpec] = [
    ModelSpec("gpt-4o-mini", "openai", ProviderKind.REMOTE, None, "optional-paid", ["chat", "reasoning", "vision"]),
    ModelSpec("claude-sonnet-4", "anthropic", ProviderKind.REMOTE, None, "optional-paid", ["chat", "reasoning", "vision"]),
    ModelSpec("gemini-2.5-flash", "google", ProviderKind.REMOTE, None, "optional-paid", ["chat", "reasoning", "vision"]),
]


def _mode() -> str:
    return os.getenv("HARNESS_MODE", "free").lower()


def _is_offline() -> bool:
    return _mode() in ("offline", "zero-cost")


def list_models(allow_paid: bool = False) -> List[ModelSpec]:
    if _is_offline():
        return FREE_MODELS
    if allow_paid:
        return FREE_MODELS + PAID_MODELS
    return FREE_MODELS


def resolve_model(name: Optional[str] = None) -> ModelSpec:
    env_name = os.getenv("HARNESS_MODEL_NAME")
    target = name or env_name or FREE_MODELS[0].name
    
    for m in FREE_MODELS + PAID_MODELS:
        if m.name == target:
            if m.cost == "optional-paid" and _is_offline():
                logger.warning("Paid model '%s' blocked, falling back to %s", target, FREE_MODELS[0].name)
                return FREE_MODELS[0]
            return m
    return FREE_MODELS[0]


def guard_paid_access(model: ModelSpec) -> None:
    if model.cost == "optional-paid" and _is_offline():
        raise PermissionError(
            f"Paid dependency '{model.name}' blocked in HARNESS_MODE={_mode()}. "
            f"Fallback to {FREE_MODELS[0].name}."
        )


def describe_router() -> Dict[str, Any]:
    return {
        "mode": _mode(),
        "free_models": [m.name for m in FREE_MODELS],
        "paid_models": [m.name for m in PAID_MODELS],
        "active": resolve_model().name,
        "offline": _is_offline(),
    }


class ModelRouterPlugin:
    def __init__(self):
        self.manifest = None
        self._active_model = None
    
    async def load(self) -> bool:
        self._active_model = resolve_model()
        logger.info("Model router loaded (active=%s)", self._active_model.name)
        return True
    
    async def start(self) -> bool:
        logger.info("Model router started")
        return True
    
    async def stop(self) -> bool:
        return True
    
    def get_active_model(self) -> ModelSpec:
        return self._active_model
    
    def list_models(self, allow_paid: bool = False) -> List[ModelSpec]:
        return list_models(allow_paid)
    
    async def health(self) -> Dict[str, Any]:
        return {"status": "healthy", "type": "model_router", **describe_router()}


async def create(kernel: Any) -> ModelRouterPlugin:
    return ModelRouterPlugin()
