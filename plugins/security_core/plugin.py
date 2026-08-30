
"""
Security Core — permission boundaries, sandboxing, secret management.

This is a CORE plugin that cannot be disabled.
Inspired by Hermes Agent security model + DeerFlow 3-ring governance.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FULL = "full"


@dataclass
class SecurityPolicy:
    allow_network: bool = True
    allow_shell: bool = True
    allow_filesystem_write: bool = True
    allowed_domains: list[str] = field(default_factory=list)
    blocked_commands: list[str] = field(default_factory=lambda: [
        "rm -rf /", "sudo", "chmod 777", "mkfs", "dd if="
    ])


class SecurityCore:
    """Security core plugin — cannot be disabled."""
    
    def __init__(self):
        self.manifest = None
        self._policy = SecurityPolicy()
        self._audit_log: list[dict[str, Any]] = []
    
    async def load(self) -> bool:
        logger.info("Security core loaded")
        return True
    
    async def start(self) -> bool:
        logger.info("Security core started")
        return True
    
    async def stop(self) -> bool:
        return True
    
    def check_permission(self, action: str, context: dict[str, Any]) -> bool:
        """Check if an action is permitted."""
        risk = self._assess_risk(action, context)
        
        if risk == RiskLevel.LOW:
            return True
        elif risk == RiskLevel.MEDIUM:
            return self._policy.allow_network
        elif risk == RiskLevel.HIGH:
            return self._policy.allow_shell
        elif risk == RiskLevel.CRITICAL:
            return False
        return False
    
    def _assess_risk(self, action: str, context: dict[str, Any]) -> RiskLevel:
        """Assess risk level of an action."""
        # Critical patterns
        critical_patterns = [
            r"rm\s+-rf\s+/",
            r"sudo\s+",
            r"chmod\s+777",
            r"mkfs\.",
            r"dd\s+if=",
            r":\(\)",
            r"curl.*\|.*sh",
        ]
        
        for pattern in critical_patterns:
            if re.search(pattern, action, re.IGNORECASE):
                return RiskLevel.CRITICAL
        
        # High risk patterns
        high_patterns = [
            r"DELETE\s+FROM",
            r"DROP\s+TABLE",
            r"eval\s*\(",
            r"exec\s*\(",
            r"subprocess\.",
        ]
        
        for pattern in high_patterns:
            if re.search(pattern, action, re.IGNORECASE):
                return RiskLevel.HIGH
        
        # Medium risk
        if any(x in action.lower() for x in ["http", "url", "fetch", "request"]):
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def sanitize_input(self, content: str, source: str) -> str:
        """Sanitize untrusted input."""
        # Mark as untrusted
        marked = f"<!-- UNTRUSTED CONTENT FROM {source} -->\n{content}"
        
        # Remove potential injection patterns
        patterns = [
            r"disregard.*prior.*directives",
            r"ignore.*previous.*instructions",
            r"system.*prompt.*override",
            r"new.*instructions.*follow",
            r"reveal.*secrets?",
            r"grant.*access",
        ]
        
        for pattern in patterns:
            marked = re.sub(pattern, "[REDACTED]", marked, flags=re.IGNORECASE)
        
        return marked
    
    def audit(self, action: str, result: str, context: dict[str, Any]):
        """Log an action to the audit log."""
        entry = {
            "action": action,
            "result": result,
            "context": context,
            "hash": hashlib.sha256(f"{action}{result}".encode()).hexdigest()[:16],
        }
        self._audit_log.append(entry)
    
    async def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "type": "security_core",
            "audit_entries": len(self._audit_log),
        }


async def create(kernel: Any) -> SecurityCore:
    return SecurityCore()
