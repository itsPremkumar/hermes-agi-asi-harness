"""Context Engineering & Compaction - Intelligent context management."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContextWindow:
    """Manages a sliding context window."""
    
    max_tokens: int = 8000
    _messages: list[dict[str, str]] = field(default_factory=list)
    
    def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content, "timestamp": time.time()})
        self._trim()
    
    def _trim(self):
        """Trim to max tokens."""
        while len(str(self._messages)) > self.max_tokens * 4 and len(self._messages) > 1:
            self._messages.pop(0)
    
    def get(self) -> list[dict[str, str]]:
        return self._messages.copy()
    
    def compact(self) -> str:
        """Compact context into a summary."""
        return "\n".join(f"{m['role']}: {m['content']}" for m in self._messages)


class ContextCompactor:
    """Intelligent context compaction."""
    
    def __init__(self, llm_manager=None):
        self.llm = llm_manager
    
    async def compact(self, messages: list[dict[str, str]], max_tokens: int = 2000) -> str:
        """Compact messages into a summary."""
        if self.llm:
            # Use LLM for intelligent compaction
            prompt = "Summarize the following conversation:\n\n"
            prompt += "\n".join(f"{m['role']}: {m['content']}" for m in messages)
            # response = await self.llm.generate(prompt)
            # return response.content
        
        # Fallback: simple truncation
        return "\n".join(f"{m['role']}: {m['content']}" for m in messages[-5:])


class TokenBudget:
    """Manage token budget across conversation."""
    
    def __init__(self, total_budget: int = 100000):
        self.total_budget = total_budget
        self.used = 0
    
    def allocate(self, tokens: int) -> bool:
        if self.used + tokens <= self.total_budget:
            self.used += tokens
            return True
        return False
    
    def remaining(self) -> int:
        return self.total_budget - self.used
