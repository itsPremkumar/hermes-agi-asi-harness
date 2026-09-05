"""PromptForge — prompt engineering and optimization."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PromptStatus(str, Enum):
    DRAFT = "draft"
    OPTIMIZED = "optimized"
    DEPLOYED = "deployed"


@dataclass
class Prompt:
    id: str
    name: str
    content: str
    status: PromptStatus = PromptStatus.DRAFT
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


class PromptForge:
    """Manage prompts."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._prompts: dict[str, Prompt] = {}

    def create(self, name: str, content: str) -> Prompt:
        prompt = Prompt(id=str(uuid.uuid4()), name=name, content=content)
        self._prompts[prompt.id] = prompt
        return prompt

    def optimize(self, prompt_id: str) -> bool:
        if prompt_id in self._prompts:
            self._prompts[prompt_id].status = PromptStatus.OPTIMIZED
            return True
        return False

    def deploy(self, prompt_id: str) -> bool:
        if prompt_id in self._prompts:
            self._prompts[prompt_id].status = PromptStatus.DEPLOYED
            return True
        return False

    def get(self, prompt_id: str) -> Prompt | None:
        return self._prompts.get(prompt_id)

    def list_all(self) -> list[Prompt]:
        return list(self._prompts.values())

    def count(self) -> int:
        return len(self._prompts)
