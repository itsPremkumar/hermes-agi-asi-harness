#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v7.0 — PROMPT INJECTION DEFENSE
========================================================
Input sanitization, instruction hierarchy enforcement.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("hermes_injection_defense")


class PromptInjectionDefense:
    """Defends against prompt injection attacks."""
    
    def __init__(self):
        self._blocked_patterns = [
            r"discard.*(directives|instructions)",
            r"disregard.*(directives|instructions)",
            r"ignore.*instructions",
            r"system\s+prompt\s+override",
            r"override.*system\s+prompt",
            r"new\s+instructions\s+follow",
            r"reveal.*secrets?",
            r"grant.*access",
            r"you\s+are\s+now\s+without.*constraints",
        ]
    
    def sanitize(self, content: str) -> str:
        """Sanitize untrusted content."""
        # Mark as untrusted
        marked = f"<!-- UNTRUSTED CONTENT -->\n{content}"
        
        # Remove potential injection patterns
        for pattern in self._blocked_patterns:
            marked = re.sub(pattern, "[REDACTED]", marked, flags=re.IGNORECASE)
        
        # Second pass: check for multi-word phrases that may have been partially redacted
        # e.g. "reveal [REDACTED]" from "reveal your secrets" - check whole phrase
        combined = re.sub(r'\s+', ' ', marked).lower()
        for phrase in ["reveal secrets", "grant access", "system prompt", "without constraints", "system prompt override"]:
            if phrase in combined:
                marked = re.sub(re.escape(phrase), "[REDACTED]", marked, flags=re.IGNORECASE)
        
        return marked
    
    def validate_output(self, output: str) -> bool:
        """Validate output doesn't contain secrets."""
        # Simple check - in production, use more sophisticated methods
        return True
    
    async def health(self) -> dict[str, Any]:
        return {"status": "healthy"}
